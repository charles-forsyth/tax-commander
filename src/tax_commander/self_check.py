import os
import sys
import tempfile
import shutil
import logging
from datetime import datetime
from .db_manager import DBManager
from .calculator import TaxCalculator
from .reporter import TaxReporter
from .biller import TaxBiller

class SelfCheckRunner:
    def __init__(self, config):
        self.config = config
        # Use a temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="tax_commander_self_check_")
        self.db_path = os.path.join(self.temp_dir, "self_check.db")
        
        # Locate schema (reusing logic from main.py conceptually)
        # We need to find the schema file. 
        # Since we are inside the package, we can look relative to this file.
        self.schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        self.db = DBManager(db_path=self.db_path, schema_path=self.schema_path)
        self.calc = TaxCalculator(default_issue_date="2025-03-01")
        
        # Override config for safety
        self.test_config = config.copy()
        self.test_config['system'] = self.test_config.get('system', {}).copy()
        self.test_config['system']['database_file'] = self.db_path
        self.test_config['system']['bill_output_dir'] = os.path.join(self.temp_dir, "bills")
        
        self.reporter = TaxReporter(self.db, self.test_config)
        self.biller = TaxBiller(output_dir=self.test_config['system']['bill_output_dir'], org_config=self.test_config)

    def run(self):
        print(f"🚀 Starting Self-Check in temporary environment: {self.temp_dir}")
        steps = [
            ("Initialize Database", self._init_db),
            ("Import Dummy Data", self._import_data),
            ("Scenario: Discount Payment", self._pay_discount),
            ("Scenario: Penalty Payment", self._pay_penalty),
            ("Scenario: Reject Penny Short", self._reject_short),
            ("Generate Monthly Report", self._report),
        ]
        
        success = True
        for name, func in steps:
            print(f"  Running: {name}...", end=" ", flush=True)
            try:
                func()
                print("✅ PASS")
            except Exception as e:
                print(f"❌ FAIL: {e}")
                success = False
                break
        
        self._cleanup()
        
        if success:
            print("\n✨ Self-Check Completed Successfully! System is ready.")
            return True
        else:
            print("\n⚠️ Self-Check Failed. Please review errors.")
            return False

    def _init_db(self):
        # DBManager initializes in __init__, so just verify
        if not os.path.exists(self.db_path):
            raise Exception("Database file not created.")

    def _import_data(self):
        self.db.connect()
        # Add P-001 (Discount payer)
        self.db.conn.execute("""
            INSERT INTO tax_duplicate 
            (parcel_id, owner_name, property_address, bill_number, assessment_value, 
             face_tax_amount, discount_amount, penalty_amount, tax_type, bill_issue_date, is_installment_plan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("P-001", "Test Owner 1", "1 Main St", "B001", 100000, 450.00, 441.00, 495.00, "Real Estate", "2025-03-01", 0))
        
        # Add P-002 (Penalty payer)
        self.db.conn.execute("""
            INSERT INTO tax_duplicate 
            (parcel_id, owner_name, property_address, bill_number, assessment_value, 
             face_tax_amount, discount_amount, penalty_amount, tax_type, bill_issue_date, is_installment_plan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("P-002", "Test Owner 2", "2 Main St", "B002", 100000, 450.00, 441.00, 495.00, "Real Estate", "2025-03-01", 0))
        
        self.db.conn.commit()
        self.db.disconnect()

    def _pay_discount(self):
        self.db.connect()
        parcel = self.db.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id='P-001'").fetchone()
        
        # Pay Exact Discount on April 15
        is_valid, msg, code = self.calc.validate_payment(parcel, 441.00, "2025-04-15")
        if not is_valid:
            raise Exception(f"Validation failed: {msg}")
            
        period = self.calc.determine_period("2025-04-15", parcel['bill_issue_date'])
        if period != "DISCOUNT":
            raise Exception(f"Wrong period detected: {period}")
            
        tx_data = {
            'date_received': "2025-04-15", 'postmark_date': "2025-04-15",
            'parcel_id': "P-001", 'amount_paid': 441.00,
            'check_number': "101", 'payment_method': 'CHECK',
            'payment_period': period
        }
        self.db.add_transaction(tx_data)
        self.db.disconnect()

    def _pay_penalty(self):
        self.db.connect()
        parcel = self.db.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id='P-002'").fetchone()
        
        # Pay Exact Penalty on July 15
        is_valid, msg, code = self.calc.validate_payment(parcel, 495.00, "2025-07-15")
        if not is_valid:
            raise Exception(f"Validation failed: {msg}")
            
        period = self.calc.determine_period("2025-07-15", parcel['bill_issue_date'])
        if period != "PENALTY":
            raise Exception(f"Wrong period detected: {period}")
            
        tx_data = {
            'date_received': "2025-07-15", 'postmark_date': "2025-07-15",
            'parcel_id': "P-002", 'amount_paid': 495.00,
            'check_number': "102", 'payment_method': 'CHECK',
            'payment_period': period
        }
        self.db.add_transaction(tx_data)
        self.db.disconnect()

    def _reject_short(self):
        self.db.connect()
        parcel = self.db.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id='P-001'").fetchone()
        
        # Try to pay $440.99 (Short)
        is_valid, msg, code = self.calc.validate_payment(parcel, 440.99, "2025-04-15")
        if is_valid:
            raise Exception("Failed to reject penny-short payment")
        
        if "REJECTED_UNDER" not in code:
            raise Exception(f"Wrong rejection code: {code}")
        self.db.disconnect()

    def _report(self):
        # Just run the generation to ensure no crashes
        # Redirect stdout to avoid clutter
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            self.reporter.generate_monthly_report(4, 2025)
        
        output = f.getvalue()
        if "TOTAL REMITTED" not in output:
            raise Exception("Report generation output suspicious")

    def _cleanup(self):
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
