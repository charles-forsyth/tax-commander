#!/usr/bin/env python3

import argparse
import csv
import sys
import yaml
import logging
import subprocess
import os
import glob
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .db_manager import DBManager
from .calculator import TaxCalculator
from .ingest import IngestManager
from .reporter import TaxReporter
from .biller import TaxBiller
from .printer import PrintManager, LabelGenerator

def load_config(config_path=None):
    """
    Load configuration from a specific path or search standard locations.
    Priority:
    1. CLI Argument (if provided)
    2. Current Directory (config.yaml)
    3. User Config Directory (~/.config/tax-commander/config.yaml)
    4. Home Directory (~/.tax-commander.yaml)
    """
    search_paths = []
    
    if config_path:
        search_paths.append(config_path)
    
    # Standard locations
    search_paths.extend([
        os.path.join(os.getcwd(), "config.yaml"),
        os.path.expanduser("~/.config/tax-commander/config.yaml"),
        os.path.expanduser("~/.tax-commander.yaml"),
    ])

    for path in search_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    print(f"Loading config from: {path}")
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading config from {path}: {e}")
    
    print("Warning: No config file found. Using defaults.")
    return {}

def main():
    # Pre-parse args to check for --config before full parsing
    # This allows us to load the config *before* setting up the rest of the CLI
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--config', help='Path to configuration file')
    args, _ = pre_parser.parse_known_args()

    # Load Config
    config = load_config(args.config)
    
    # Defaults from config or fallback
    sys_conf = config.get('system', {})
    fin_conf = config.get('financial', {})
    org_conf = config.get('organization', {})
    def_conf = config.get('defaults', {})

    db_path = sys_conf.get('database_file', 'tax_commander.db')
    
    schema_path = sys_conf.get('schema_file')
    
    # If not in config, or if configured path doesn't exist locally, try to find it bundled
    if not schema_path or not os.path.exists(schema_path):
        bundled_schema = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if os.path.exists(bundled_schema):
             schema_path = bundled_schema

    log_file = sys_conf.get('log_file', 'tax_commander.log')
    bill_output_dir = sys_conf.get('bill_output_dir', 'tax_bills')
    default_issue_date = def_conf.get('bill_issue_date', '2025-03-01')

    # Configure Logging
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Tax Commander CLI")
    
    # Mode Selection
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # 1. Initialize DB
    subparsers.add_parser('init-db', help='Initialize the Database')

    # 2. Import Duplicate (CSV)
    import_parser = subparsers.add_parser('import-duplicate', help='Import Tax Duplicate CSV')
    import_parser.add_argument('file', help='Path to CSV file')

    # 3. Pay (Manual Entry)
    pay_parser = subparsers.add_parser('pay', help='Record a Payment')
    pay_parser.add_argument('--parcel', required=True, help='Parcel ID')
    pay_parser.add_argument('--amount', type=float, required=True, help='Amount Paid')
    pay_parser.add_argument('--date', required=True, help='Postmark Date (YYYY-MM-DD)')
    pay_parser.add_argument('--check', default='CASH', help='Check Number')
    pay_parser.add_argument('--installment-num', type=int, help='Installment number for partial payments')

    # 4. Ingest (Image Processing)
    ingest_parser = subparsers.add_parser('ingest', help='Process an image (e.g., check) for payment details')
    ingest_parser.add_argument('file', help='Path to image file')

    # 5. Report
    report_parser = subparsers.add_parser('report', help='Generate Monthly Report')
    report_parser.add_argument('--month', type=int, required=True)
    report_parser.add_argument('--year', type=int, required=True)

    # 6. Receipt
    receipt_parser = subparsers.add_parser('receipt', help='Generate Receipt')
    receipt_parser.add_argument('tx_id', type=int, help='Transaction ID')

    # 7. Return List
    subparsers.add_parser('return-list', help='Generate Return List of Unpaid Taxes')

    # 8. Deposit Slip
    deposit_parser = subparsers.add_parser('deposit-slip', help='Generate Deposit Slip')
    deposit_parser.add_argument('date', help='Date of Receipt (YYYY-MM-DD)')

    # 9. Close Month
    close_month_parser = subparsers.add_parser('close-month', help='Close a tax month (lock transactions)')
    close_month_parser.add_argument('--month', type=int, required=True)
    close_month_parser.add_argument('--year', type=int, required=True)

    # 10. Exonerate
    exon_parser = subparsers.add_parser('exonerate', help='Process an Exoneration (forgive tax)')
    exon_parser.add_argument('--parcel', required=True, help='Parcel ID')
    exon_parser.add_argument('--amount', type=float, required=True, help='Amount to Exonerate')
    exon_parser.add_argument('--date', required=True, help='Date of Exoneration (YYYY-MM-DD)')
    exon_parser.add_argument('--reason', required=True, help='Reason (e.g., Death, Indigent)')

    # 11. NSF Reversal
    nsf_parser = subparsers.add_parser('nsf', help='Record a Bounced Check (NSF)')
    nsf_parser.add_argument('tx_id', type=int, help='Original Transaction ID to Reverse')

    # 12. Audit
    audit_parser = subparsers.add_parser('audit', help='View Audit Log (Change History)')
    audit_parser.add_argument('--limit', type=int, default=20, help='Number of records to view (default: 20)')

    # 13. Generate Bills
    gen_bills_parser = subparsers.add_parser('generate-bills', help='Generate PDF Tax Bills for mailing')
    gen_bills_parser.add_argument('--type', default='Township_County',
                                  choices=['Township_County', 'School'], 
                                  help='Type of bill to generate (Township_County or School)')

    # 14. Status Report (Dashboard)
    subparsers.add_parser('status', help='Generate Real-Time Collection Status Report')

    # 15. Export Mailing Labels (CSV)
    subparsers.add_parser('export-labels', help='Export mailing labels to CSV for Avery 5160')

    # 16. Reprint Bill
    reprint_parser = subparsers.add_parser('reprint-bill', help='Reprint a tax bill for a specific parcel')
    reprint_parser.add_argument('--parcel', required=True, help='Parcel ID')
    reprint_parser.add_argument('--type', default='Township_County', 
                                choices=['Township_County', 'School'], 
                                help='Type of bill to reprint')

    # 17. Turnover Report (Lien List)
    subparsers.add_parser('turnover-report', help='Generate Delinquency Turnover Report (Lien List) for Tax Claim Bureau')

    # 18. Web Dashboard
    subparsers.add_parser('dashboard', help='Launch the Interactive Web Dashboard')

    # 19. List Printers
    subparsers.add_parser('list-printers', help='List available CUPS printers')

    # 20. Print Bills (Batch)
    print_bills_parser = subparsers.add_parser('print-bills', help='Batch print tax bills from a folder')
    print_bills_parser.add_argument('--folder', required=True, help='Path to folder containing PDF bills')
    print_bills_parser.add_argument('--printer', help='Name of the printer (from list-printers). Default: System default.')

    # 21. Print Labels (PDF Generation + Print)
    print_labels_parser = subparsers.add_parser('print-labels', help='Generate and print Avery 5160 labels')
    print_labels_parser.add_argument('--csv', help='Path to labels CSV. Defaults to most recent Mailing_Labels_*.csv')
    print_labels_parser.add_argument('--printer', help='Name of the printer. If omitted, only generates the PDF.')

    # 22. Update Parcel (Address/Name Change)
    update_parser = subparsers.add_parser('update-parcel', help='Update parcel owner name or mailing address')
    update_parser.add_argument('--parcel', required=True, help='Parcel ID')
    update_parser.add_argument('--name', help='New Owner Name')
    update_parser.add_argument('--address', help='New Mailing Address')

    # 23. Add Interim Parcel
    interim_parser = subparsers.add_parser('add-interim', help='Add a new interim parcel (mid-year)')
    interim_parser.add_argument('--parcel', required=True, help='New Parcel ID')
    interim_parser.add_argument('--name', required=True, help='Owner Name')
    interim_parser.add_argument('--address', required=True, help='Mailing Address')
    interim_parser.add_argument('--assessment', type=float, required=True, help='Assessed Value')
    interim_parser.add_argument('--face', type=float, required=True, help='Face Tax Amount')
    interim_parser.add_argument('--discount', type=float, required=True, help='Discount Amount')
    interim_parser.add_argument('--penalty', type=float, required=True, help='Penalty Amount')
    interim_parser.add_argument('--issue-date', required=True, help='Bill Issue Date (YYYY-MM-DD)')

    # 24. Settlement Report
    subparsers.add_parser('settlement', help='Generate Annual Settlement Report (Balancing)')

    # 25. Lookup (Customer Service View)
    lookup_parser = subparsers.add_parser('lookup', help='Lookup Parcel Details & History')
    lookup_parser.add_argument('term', help='Parcel ID or Owner Name (partial)')

    args = parser.parse_args()
    
    db = DBManager(db_path=db_path, schema_path=schema_path)
    calc = TaxCalculator(default_issue_date=default_issue_date)
    ingest_manager = IngestManager(db, config)
    reporter = TaxReporter(db, config)
    biller = TaxBiller(output_dir=bill_output_dir, org_config=config)
    printer = PrintManager(config)
    label_gen = LabelGenerator()

    if args.command == 'init-db':
        print("Database initialized successfully.")
    
    elif args.command == 'import-duplicate':
        db.backup_db()
        print(f"Importing duplicate from {args.file}...")
        db.connect() # Connect for this command
        try:
            with open(args.file, 'r') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    # Updated INSERT to include new schema fields
                    db.conn.execute("""
                        INSERT OR REPLACE INTO tax_duplicate 
                        (parcel_id, owner_name, property_address, mailing_address, bill_number, 
                         assessment_value, homestead_exclusion, farmstead_exclusion, 
                         face_tax_amount, discount_amount, penalty_amount,
                         tax_type, bill_issue_date, is_installment_plan)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row['parcel_id'], row['owner_name'], row['property_address'], 
                        row.get('mailing_address', row['property_address']),
                        row['bill_number'],
                        row['assessment_value'], 
                        row.get('homestead_exclusion', 0.0),
                        row.get('farmstead_exclusion', 0.0),
                        row['face_tax_amount'], row['discount_amount'], row['penalty_amount'],
                        row['tax_type'], row.get('bill_issue_date', default_issue_date), int(row.get('is_installment_plan', 0))
                    ))
                    count += 1
                db.conn.commit()
                print(f"Imported {count} records.")
        except Exception as e:
            print(f"Error importing: {e}")
        finally:
            db.disconnect() # Disconnect after this command

    elif args.command == 'pay':
        db.backup_db()
        print(f"Processing payment for {args.parcel}...")
        
        db.connect() # Open connection once at the start
        try:
            parcel = db.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id = ?", (args.parcel,)).fetchone()
            
            if not parcel:
                print(f"Error: Parcel {args.parcel} not found.")
                sys.exit(1)

            is_valid, msg, code = calc.validate_payment(parcel, args.amount, args.date, args.installment_num)
            
            if not is_valid:
                print(f"VALIDATION FAILED: {msg} ({code})")
                
                # --- Record the rejected payment attempt --- 
                rejected_tx_data = {
                    'date_received': args.date, 
                    'postmark_date': args.date,
                    'parcel_id': args.parcel,
                    'amount_paid': args.amount,
                    'check_number': args.check,
                    'payment_method': 'CHECK' if args.check != 'CASH' else 'CASH',
                    'transaction_type': 'REJECTED_PAYMENT', # New transaction type
                    'notes': f"Rejected: {msg} ({code})",
                    'balance_remaining': parcel['face_tax_amount'] # Assumed original balance remains
                }
                try:
                    db.add_transaction(rejected_tx_data) # This now uses the already open connection
                    # Fetch last rowid *through the main db object's connection*
                    db.conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                    print(f"Recorded rejected payment attempt for {args.parcel} (ID: {db.conn.execute('SELECT last_insert_rowid()').fetchone()[0]})")
                    
                    # --- Generate Rejection Notice PDF ---
                    reporter.generate_rejection_letter(
                        dict(parcel), 
                        args.amount,
                        f"{msg} ({code})",
                        args.check
                    )
                    
                except Exception as e:
                    print(f"Database Error recording rejected payment: {e}")
                
                sys.exit(1) # Still exit to indicate command failure

            period = calc.determine_period(args.date, parcel['bill_issue_date'])
            
            tx_data = {
                'date_received': args.date, 
                'postmark_date': args.date,
                'parcel_id': args.parcel,
                'amount_paid': args.amount,
                'check_number': args.check,
                'payment_method': 'CHECK' if args.check != 'CASH' else 'CASH',
                'payment_period': period,
                'installment_number': args.installment_num
            }
            
            try:
                tx_id = db.add_transaction(tx_data) # This uses the already open connection
                print(f"SUCCESS: Payment recorded. ID: {tx_id}. Period: {period}")
            except Exception as e:
                print(f"Database Error: {e}")
        finally:
            db.disconnect() # Close connection once at the end

    elif args.command == 'ingest':
        db.backup_db()
        print(f"Starting image ingestion for {args.file}...")
        extracted_info = ingest_manager.process_image(args.file)

        if extracted_info:
            db.connect() # Connect for this section
            try:
                parcel = db.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id = ?", (extracted_info['found_parcel_id'],)).fetchone()
                
                if not parcel:
                    print(f"Error: Parcel {extracted_info['found_parcel_id']} not found in database after ingestion.")
                    sys.exit(1)

                is_valid, msg, code = calc.validate_payment(parcel, float(extracted_info['amount']), extracted_info['postmark_date'])
                
                if not is_valid:
                    print(f"INGESTION VALIDATION FAILED: {msg} ({code})")
                    # --- Record the rejected payment attempt during ingestion ---
                    rejected_tx_data = {
                        'date_received': extracted_info['postmark_date'], 
                        'postmark_date': extracted_info['postmark_date'],
                        'parcel_id': extracted_info['found_parcel_id'],
                        'amount_paid': float(extracted_info['amount']),
                        'check_number': extracted_info['check_number'],
                        'payment_method': 'CHECK', # Assume check for ingestion
                        'transaction_type': 'REJECTED_PAYMENT',
                        'notes': f"Rejected (Ingest): {msg} ({code})",
                        'balance_remaining': parcel['face_tax_amount']
                    }
                    try:
                        db.add_transaction(rejected_tx_data)
                        print(f"Recorded rejected payment attempt during ingestion for {extracted_info['found_parcel_id']} (ID: {db.conn.execute('SELECT last_insert_rowid()').fetchone()[0]})")
                    except Exception as e:
                        print(f"Database Error recording rejected ingestion payment: {e}")
                    # --- END NEW ---
                    sys.exit(1) # Still exit to indicate command failure
                
                period = calc.determine_period(extracted_info['postmark_date'], parcel['bill_issue_date'])
                tx_data = {
                    'date_received': extracted_info['postmark_date'], 
                    'postmark_date': extracted_info['postmark_date'],
                    'parcel_id': extracted_info['found_parcel_id'],
                    'amount_paid': float(extracted_info['amount']),
                    'check_number': extracted_info['check_number'],
                    'payment_method': 'CHECK',
                    'payment_period': period
                }
                try:
                    tx_id = db.add_transaction(tx_data)
                    print(f"SUCCESS: Ingested payment recorded. ID: {tx_id}. Parcel: {extracted_info['found_parcel_id']}. Period: {period}")
                except Exception as e:
                    print(f"Database Error during ingestion: {e}")
            finally:
                db.disconnect() # Disconnect after this section
        else:
            print("Image ingestion cancelled or failed.")

    elif args.command == 'report':
        db.connect()
        try:
            reporter.generate_monthly_report(args.month, args.year)
        finally:
            db.disconnect()

    elif args.command == 'receipt':
        db.connect()
        try:
            reporter.generate_receipt(args.tx_id)
        finally:
            db.disconnect()

    elif args.command == 'return-list':
        db.connect()
        try:
            reporter.generate_return_list()
        finally:
            db.disconnect()

    elif args.command == 'deposit-slip':
        db.connect()
        try:
            reporter.create_deposit_slip(args.date)
        finally:
            db.disconnect()

    elif args.command == 'close-month':
        db.backup_db()
        db.connect()
        try:
            db.close_month(args.month, args.year)
        except Exception as e:
            print(f"Error closing month: {e}")
        finally:
            db.disconnect()

    elif args.command == 'exonerate':
        db.backup_db()
        tx_data = {
            'date_received': args.date,
            'postmark_date': args.date,
            'parcel_id': args.parcel,
            'transaction_type': 'EXONERATION',
            'payment_method': 'NONE',
            'amount_paid': args.amount,
            'notes': args.reason
        }
        db.connect()
        try:
            tx_id = db.add_transaction(tx_data)
            print(f"SUCCESS: Exoneration recorded. ID: {tx_id}. Reason: {args.reason}")
        except Exception as e:
            print(f"Database Error: {e}")
        finally:
            db.disconnect()

    elif args.command == 'nsf':
        db.backup_db()
        db.connect()
        try:
            db.process_nsf_reversal(args.tx_id)
        except Exception as e:
            print(f"Error processing NSF: {e}")
        finally:
            db.disconnect()

    elif args.command == 'audit':
        print(f"\n--- System Audit Log (Last {args.limit} Changes) ---")
        db.connect()
        try:
            query = f"SELECT * FROM change_log ORDER BY log_id DESC LIMIT {args.limit}"
            cursor = db.conn.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                print("No audit records found.")
            else:
                print(f"{ 'Time':<20} | { 'Table':<15} | { 'ID':<5} | { 'Action':<6} | { 'Field':<10} | { 'Old':<10} -> { 'New':<10}")
                print("-" * 90)
                for row in rows:
                    ts = row['timestamp'][:19].replace('T', ' ')
                    print(f"{ts:<20} | {row['table_name']:<15} | {row['record_id']:<5} | {row['action_type']:<6} | {row['field_name'] or '-':<10} | {row['old_value'] or '-':<10} -> {row['new_value'] or '-':<10}")
        except Exception as e:
            print(f"Error accessing audit log (maybe run init-db first?): {e}")
        finally:
            db.disconnect()

    elif args.command == 'generate-bills':
        db.connect()
        try:
            biller.generate_all_bills(db, args.type)
        finally:
            db.disconnect()

    elif args.command == 'status':
        print("\n--- Generating Real-Time Status Report ---")
        db.connect()
        
        # 1. High-Level Totals
        try:
            total_parcels = db.conn.execute("SELECT COUNT(*) FROM tax_duplicate").fetchone()[0]
            total_face_value = db.conn.execute("SELECT SUM(face_tax_amount) FROM tax_duplicate").fetchone()[0] or 0.0
            total_collected = db.conn.execute("SELECT SUM(amount_paid) FROM transactions WHERE transaction_type='PAYMENT'").fetchone()[0] or 0.0
            
            percent_collected = (total_collected / total_face_value * 100) if total_face_value > 0 else 0.0

            # 2. Status Breakdown
            status_counts = db.conn.execute("SELECT status, COUNT(*) FROM tax_duplicate GROUP BY status").fetchall()
            status_dict = {row[0]: row[1] for row in status_counts}
            
            # 3. Tax Type Breakdown
            type_stats = db.conn.execute("""
                SELECT 
                    d.tax_type, 
                    SUM(t.amount_paid) as collected,
                    COUNT(DISTINCT t.parcel_id) as count
                FROM transactions t
                JOIN tax_duplicate d ON t.parcel_id = d.parcel_id
                WHERE t.transaction_type='PAYMENT'
                GROUP BY d.tax_type
            """).fetchall()

            db.disconnect()

            # Build Report Text (Markdown)
            report_lines = []
            report_lines.append(f"# Tax Collection Status Report")
            report_lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            
            report_lines.append("## 1. High-Level Summary")
            report_lines.append(f"*   **Total Parcels:** {total_parcels}")
            report_lines.append(f"*   **Total Face Value:** ${total_face_value:,.2f}")
            report_lines.append(f"*   **Total Collected (YTD):** ${total_collected:,.2f}")
            report_lines.append(f"*   **Collection Rate:** {percent_collected:.1f}%")

            report_lines.append("## 2. Parcel Status Breakdown")
            for status, count in status_dict.items():
                report_lines.append(f"*   **{status}:** {count} parcels")
            report_lines.append("")

            report_lines.append("## 3. Revenue by Tax Type")
            report_lines.append("| Tax Type | Parcels Paid | Amount Collected |")
            report_lines.append("| :--- | :---: | :---: |")
            if not type_stats:
                 report_lines.append("| (No Payments Yet) | - | - |")
            else:
                for row in type_stats:
                    report_lines.append(f"| {row[0]} | {row[2]} | ${row[1]:,.2f} |")
            report_lines.append("")

            report_lines.append("## 4. Operational Notes")
            report_lines.append(f"*   Run `report` command for detailed monthly remittance.")
            report_lines.append(f"*   Run `return-list` to export unpaid parcels.")

            full_report = "\n".join(report_lines)
            
            # Output to Console
            print(full_report)
            
            # Save to File
            filename = f"Status_Report_{datetime.now().strftime('%Y-%m-%d')}.md"
            with open(filename, "w") as f:
                f.write(full_report)
            print(f"\nStatus report saved to: {filename}")
        except Exception as e:
            print(f"Error generating status report: {e}")
            if db.conn: db.disconnect()

    elif args.command == 'export-labels':
        db.connect()
        try:
            reporter.export_mailing_labels()
        finally:
            db.disconnect()

    elif args.command == 'reprint-bill':
        db.connect()
        try:
            biller.reprint_bill(db, args.parcel, args.type)
        finally:
            db.disconnect()

    elif args.command == 'turnover-report':
        db.connect()
        try:
            reporter.generate_turnover_report()
        finally:
            db.disconnect()

    elif args.command == 'dashboard':
        print("Launching Tax Commander Dashboard...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dashboard_path = os.path.join(script_dir, "dashboard.py")
        try:
            subprocess.run(["streamlit", "run", dashboard_path], check=True)
        except KeyboardInterrupt:
            print("\nDashboard closed.")
        except Exception as e:
            print(f"Error running dashboard: {e}")

    elif args.command == 'list-printers':
        printer.list_printers()

    elif args.command == 'print-bills':
        printer.batch_print_folder(args.folder, args.printer)

    elif args.command == 'print-labels':
        csv_file = args.csv
        if not csv_file:
            files = glob.glob("Mailing_Labels_*.csv")
            if not files:
                print("No mailing label CSV files found. Run 'export-labels' first.")
                sys.exit(1)
            csv_file = max(files, key=os.path.getctime)
            print(f"Using most recent labels file: {csv_file}")
        
        pdf_file = label_gen.generate_pdf(csv_file)
        
        if args.printer and pdf_file:
            printer.print_file(pdf_file, args.printer)
        elif pdf_file:
            print(f"PDF generated at {pdf_file}. To print, run again with --printer <name>.")

    elif args.command == 'update-parcel':
        db.backup_db()
        if not args.name and not args.address:
            print("Error: Must specify --name or --address to update.")
            sys.exit(1)
        db.connect()
        try:
            db.update_parcel_info(args.parcel, args.name, args.address)
        except Exception as e:
            print(f"Error updating parcel: {e}")
        finally:
            db.disconnect()

    elif args.command == 'add-interim':
        db.backup_db()
        data = {
            'parcel_id': args.parcel,
            'owner_name': args.name,
            'property_address': args.address, 
            'mailing_address': args.address,
            'bill_number': f"INT-{args.parcel}",
            'assessment_value': args.assessment,
            'homestead_exclusion': 0.0, # Interim parcels typically don't have this until final bill
            'farmstead_exclusion': 0.0,
            'face_tax_amount': args.face,
            'discount_amount': args.discount,
            'penalty_amount': args.penalty,
            'tax_type': 'Real Estate',
            'bill_issue_date': args.issue_date
        }
        db.connect()
        try:
            db.add_interim_parcel(data)
        except Exception as e:
            print(f"Error adding interim: {e}")
        finally:
            db.disconnect()

    elif args.command == 'settlement':
        db.connect()
        try:
            reporter.generate_settlement_report()
        finally:
            db.disconnect()

    elif args.command == 'lookup':
        db.connect()
        try:
            data = db.get_parcel_details(args.term)
            if not data:
                print(f"No records found matching '{args.term}'")
            else:
                p = data['parcel']
                txs = data['transactions']
                
                # Calculate Dates
                issue_date = datetime.strptime(p['bill_issue_date'], "%Y-%m-%d").date()
                discount_end = issue_date + relativedelta(months=2) - timedelta(days=1)
                face_end = issue_date + relativedelta(months=4) - timedelta(days=1)
                penalty_start = face_end + timedelta(days=1)

                print("\n" + "="*60)
                print(f" TAXPAYER STATUS CARD: {p['parcel_id']}")
                print(f" Report Date: {datetime.now().strftime('%Y-%m-%d')}")
                print("="*60)
                print(f" Owner:      {p['owner_name']}")
                print(f" Property:   {p['property_address']}")
                print(f" Mailing:    {p['mailing_address']}")
                print(f" Bill #:     {p['bill_number']} ({p['tax_type']})")
                print(f" Issue Date: {p['bill_issue_date']}")
                print("-" * 60)
                print(f" Assessment: ${p['assessment_value']:,.2f}")
                print("-" * 60)
                print(f" DISCOUNT:   ${p['discount_amount']:,.2f}  (Ends: {discount_end})")
                print(f" FACE:       ${p['face_tax_amount']:,.2f}  (Ends: {face_end})")
                print(f" PENALTY:    ${p['penalty_amount']:,.2f}  (Starts: {penalty_start})")
                
                if p.get('is_installment_plan'):
                    print("-" * 60)
                    print(" INSTALLMENT PLAN (Optional):")
                    inst_amount = round(p['face_tax_amount'] / 3, 2)
                    print(f"   Payment 1: ${inst_amount:,.2f}")
                    print(f"   Payment 2: ${inst_amount:,.2f}")
                    print(f"   Payment 3: ${inst_amount:,.2f}")

                # Generate Status Paragraph
                status_msg = ""
                today = datetime.now().date()
                
                if p['status'] == 'PAID':
                    status_msg = "This bill has been PAID IN FULL. No further action is required."
                elif p['status'] == 'EXONERATED':
                    status_msg = "This bill has been EXONERATED. No balance is due."
                elif p['status'] == 'RETURNED':
                    status_msg = "This bill remains UNPAID and has been RETURNED to the County Tax Claim Bureau for collection."
                else: # UNPAID or PARTIAL
                    if today <= discount_end:
                        amount_due = p['discount_amount']
                        period_name = "DISCOUNT"
                    elif today <= face_end:
                        amount_due = p['face_tax_amount']
                        period_name = "FACE"
                    else:
                        amount_due = p['penalty_amount']
                        period_name = "PENALTY"
                    
                    status_msg = f"This bill is currently UNPAID. We are in the {period_name} period.\n The total amount due TODAY is ${amount_due:,.2f}."
                    
                    if p.get('is_installment_plan'):
                         status_msg += "\n Alternatively, if eligible, an installment payment may be made."

                print("-" * 60)
                print(f" CURRENT STATUS: [{p['status']}]")
                print(f" {status_msg}")
                print("-" * 60)
                
                if not txs:
                    print(" No transactions recorded.")
                else:
                    print(f" {'Date':<12} | {'Type':<16} | {'Method':<8} | {'Amount':<10} | {'Notes'}")
                    print("-" * 80)
                    for t in txs:
                        amt = f"${t['amount_paid']:,.2f}"
                        notes = t['notes'] if t['notes'] else ''
                        
                        # Format notes: Check number first if exists, then any other notes
                        display_notes = []
                        if t['check_number']:
                            display_notes.append(f"Ck#{t['check_number']}")
                        if notes:
                            display_notes.append(notes)
                        
                        notes_str = " | ".join(display_notes)

                        # Truncate notes if extremely long
                        if len(notes_str) > 50:
                            notes_str = notes_str[:47] + "..."

                        print(f" {t['date_received']:<12} | {t['transaction_type']:<16} | {t['payment_method'] or '-':<8} | {amt:<10} | {notes_str}")
                print("="*60 + "\n")
        except Exception as e:
            print(f"Error looking up parcel: {e}")
        finally:
            db.disconnect()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()