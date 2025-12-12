import pytest
import subprocess
import os
import sqlite3
from tax_commander.db_manager import DBManager

# Helper to run CLI
def run_cli(args, cwd):
    # args is a list, e.g. ["pay", "--parcel", "P-001", ...]
    # We call "python3 -m tax_commander.main" to simulate the CLI entry point
    cmd = ["python3", "-m", "tax_commander.main"] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result

def test_init_db(temp_env):
    res = run_cli(["init-db"], cwd=temp_env)
    assert res.returncode == 0
    assert "Database initialized successfully" in res.stdout
    assert os.path.exists(os.path.join(temp_env, "tioga_tax.db"))

def test_import_duplicate_and_pay_discount(temp_env):
    # 1. Init
    run_cli(["init-db"], cwd=temp_env)
    
    # 2. Generate Dummy Data
    csv_path = os.path.join(temp_env, "test_duplicate.csv")
    with open(csv_path, "w") as f:
        f.write("parcel_id,owner_name,property_address,bill_number,assessment_value,face_tax_amount,discount_amount,penalty_amount,tax_type,bill_issue_date,is_installment_plan\n")
        f.write("P-001,Test Owner,1 Main St,B001,100000,450.00,441.00,495.00,Real Estate,2025-03-01,0\n")

    # 3. Import
    res = run_cli(["import-duplicate", "test_duplicate.csv"], cwd=temp_env)
    assert res.returncode == 0
    
    # 4. Pay Discount (Exact)
    res = run_cli(["pay", "--parcel", "P-001", "--amount", "441.00", "--date", "2025-04-15"], cwd=temp_env)
    assert res.returncode == 0
    assert "SUCCESS" in res.stdout
    
    # Verify in DB
    # We must construct a DBManager or connect manually to the temp db
    db_path = os.path.join(temp_env, "tioga_tax.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM transactions WHERE parcel_id='P-001'").fetchone()
    conn.close()
    
    assert row is not None
    assert row['amount_paid'] == 441.00
    assert row['payment_period'] == 'DISCOUNT'

def test_pay_penny_short_rejection(temp_env):
    # Setup
    run_cli(["init-db"], cwd=temp_env)
    csv_path = os.path.join(temp_env, "test_duplicate.csv")
    with open(csv_path, "w") as f:
        f.write("parcel_id,owner_name,property_address,bill_number,assessment_value,face_tax_amount,discount_amount,penalty_amount,tax_type,bill_issue_date,is_installment_plan\n")
        f.write("P-004,Short Payer,4 Main St,B004,100000,450.00,441.00,495.00,Real Estate,2025-03-01,0\n")
    run_cli(["import-duplicate", "test_duplicate.csv"], cwd=temp_env)

    # Pay Penny Short (Should Fail)
    res = run_cli(["pay", "--parcel", "P-004", "--amount", "440.99", "--date", "2025-04-15"], cwd=temp_env)
    
    assert res.returncode == 1
    assert "VALIDATION FAILED" in res.stdout
    assert "UNDERPAYMENT" in res.stdout
    
    # Verify Rejection Logged
    db_path = os.path.join(temp_env, "tioga_tax.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM transactions WHERE parcel_id='P-004'").fetchone()
    conn.close()
    
    assert row is not None
    assert row['transaction_type'] == 'REJECTED_PAYMENT'
