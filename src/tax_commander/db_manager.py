import sqlite3
import shutil
import os
import logging
from datetime import datetime

class DBManager:
    def __init__(self, db_path="tioga_tax.db", schema_path="schema.sql"):
        self.db_path = db_path
        self.schema_path = schema_path
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Creates the DB tables if they don't exist."""
        db_exists = os.path.exists(self.db_path)
        self.connect()
        
        if not db_exists:
            print(f"Creating new database at {self.db_path}...")
            with open(self.schema_path, 'r') as f:
                schema_script = f.read()
            self.conn.executescript(schema_script)
            self.log_action("SYSTEM", "Database initialized")
            logging.info("Database initialized successfully.")
        
        self.disconnect()

    def log_db_change(self, table, record_id, action, field=None, old_val=None, new_val=None):
        """
        Records a specific data change to the internal DB change_log.
        """
        query = """
        INSERT INTO change_log (timestamp, table_name, record_id, action_type, field_name, old_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        timestamp = datetime.now().isoformat()
        
        if self.conn:
            self.conn.execute(query, (timestamp, table, str(record_id), action, field, str(old_val), str(new_val)))
        
        log_msg = f"DB_CHANGE: [{table}:{record_id}] {action} {field if field else ''} ({old_val} -> {new_val})"
        logging.info(log_msg)

    def connect(self):
        """Opens a connection to the SQLite DB."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def disconnect(self):
        """Closes the connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def backup_db(self):
        """Creates a timestamped backup."""
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = os.path.join(backup_dir, f"tioga_tax_backup_{timestamp}.db")
        
        try:
            shutil.copy2(self.db_path, backup_name)
            print(f"Database backed up to {backup_name}")
            logging.info(f"Database backup created: {backup_name}")
            
            backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("tioga_tax_backup_") and f.endswith(".db")], key=os.path.getmtime)
            
            while len(backups) > 5:
                oldest_backup = backups.pop(0)
                os.remove(oldest_backup)
                print(f"Rotated old backup: {oldest_backup}")
                
        except Exception as e:
            print(f"Backup failed: {e}")
            logging.error(f"Backup failed: {e}")

    def log_action(self, action, details):
        """Records an event in the systemI in the system log."""
        query = "INSERT INTO system_log (timestamp, action, details) VALUES (?, ?, ?)"
        # Assume self.conn is available (connected by caller)
        if self.conn:
            self.conn.execute(query, (datetime.now().isoformat(), action, details))
            self.conn.commit()
        else:
            # This case should ideally not happen if connection is managed by caller
            logging.error(f"Attempted to log action '{action}' without an active DB connection.")

    def add_transaction(self, data):
        """Adds a transaction securely."""
        date_received_str = data.get('date_received')
        if not date_received_str:
            raise ValueError("date_received is required for transaction.")

        transaction_date = datetime.strptime(date_received_str, "%Y-%m-%d")
        month = transaction_date.month
        year = transaction_date.year

        # Assume connection is already open by caller
        try:
            cursor = self.conn.cursor() # Get a cursor for explicit control

            # For REJECTED_PAYMENT, we want to log the attempt regardless of month closure status.
            # For actual payments, check if the month is closed.
            if data.get('transaction_type') != 'REJECTED_PAYMENT':
                month_closed_check_query = """
                    SELECT COUNT(*) FROM transactions
                    WHERE STRFTIME('%Y', date_received) = ? 
                    AND STRFTIME('%m', date_received) = ? 
                    AND is_closed = 1
                """
                cursor.execute(month_closed_check_query, (str(year), f'{month:02d}'))
                
                if cursor.fetchone()[0] > 0:
                    raise ValueError(f"Month {month}/{year} is already closed. Cannot add new transactions.")

            query = """
            INSERT INTO transactions (
                date_received, postmark_date, parcel_id, transaction_type, 
                payment_method, check_number, amount_paid, balance_remaining, 
                payment_period, installment_number, deposit_batch_id, 
                is_closed, image_path, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                date_received_str,
                data.get('postmark_date'),
                data['parcel_id'],
                data.get('transaction_type', 'PAYMENT'),
                data.get('payment_method'),
                data.get('check_number'),
                data['amount_paid'],
                data.get('balance_remaining', 0.0),
                data.get('payment_period'),
                data.get('installment_number'),
                data.get('deposit_batch_id'),
                data.get('is_closed', 0),
                data.get('image_path'),
                data.get('notes')
            )
            
            cursor.execute(query, params)
            
            # Determine new_status for the parcel, but only for actual payments/returns/exonerations
            # Rejected payments should NOT alter the parcel status as they are not accepted.
            if data.get('transaction_type') == 'PAYMENT':
                new_status = 'PARTIAL'
                if data.get('balance_remaining', 0.0) <= 0.009: 
                    new_status = 'PAID'
                self.update_parcel_status(data['parcel_id'], new_status)
            elif data.get('transaction_type') == 'RETURN':
                self.update_parcel_status(data['parcel_id'], 'RETURNED')
            elif data.get('transaction_type') == 'EXONERATION':
                self.update_parcel_status(data['parcel_id'], 'EXONERATED')
            # For 'REJECTED_PAYMENT', status remains whatever it was (likely 'UNPAID')

            
            self.conn.commit()
            
            new_tx_id = cursor.lastrowid
            self.log_action("TRANSACTION", f"Added transaction for {data['parcel_id']}: {data['amount_paid']}")
            self.log_db_change("transactions", new_tx_id, "INSERT", "amount_paid", "0.00", str(data['amount_paid']))
            
            return new_tx_id
        except Exception as e:
            self.conn.rollback()
            raise e


    def update_parcel_status(self, parcel_id, status):
        """Updates the status of a parcel in the master list."""
        old_status_row = self.conn.execute("SELECT status FROM tax_duplicate WHERE parcel_id = ?", (parcel_id,)).fetchone()
        old_status = old_status_row['status'] if old_status_row else 'UNKNOWN'

        query = "UPDATE tax_duplicate SET status = ? WHERE parcel_id = ?"
        self.conn.execute(query, (status, parcel_id))
        
        if old_status != status:
            self.log_db_change("tax_duplicate", parcel_id, "UPDATE", "status", old_status, status)

    def close_month(self, month, year):
        """Locks all transactions for a given month/year."""
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        query = "UPDATE transactions SET is_closed = 1 WHERE date_received >= ? AND date_received < ? AND is_closed = 0"
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, (start_date, end_date))
            count = cursor.rowcount
            self.conn.commit()
            self.log_action("CLOSE_MONTH", f"Closed {count} transactions for {month}/{year}")
            print(f"Successfully closed {count} transactions for {month}/{year}.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error closing month: {e}")

    def process_nsf_reversal(self, original_transaction_id, fee_amount=0):
        """Handles an NSF check."""
        # Assume connection is already open by caller
        try:
            row = self.conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (original_transaction_id,)).fetchone()
            if not row:
                raise ValueError("Transaction not found")
            
            reversal_data = {
                'date_received': datetime.now().strftime("%Y-%m-%d"),
                'postmark_date': datetime.now().strftime("%Y-%m-%d"),
                'parcel_id': row['parcel_id'],
                'transaction_type': 'NSF_REVERSAL',
                'payment_method': 'ADJUSTMENT',
                'check_number': row['check_number'],
                'amount_paid': -row['amount_paid'],
                'balance_remaining': row['amount_paid'],
                'payment_period': row['payment_period'],
                'installment_number': row['installment_number'],
                'notes': f"NSF Reversal for Trans ID {original_transaction_id}"
            }
            
            self.conn.execute("""
                INSERT INTO transactions (
                    date_received, postmark_date, parcel_id, transaction_type, 
                    payment_method, check_number, amount_paid, balance_remaining, 
                    payment_period, installment_number, notes
                ) VALUES (:date_received, :postmark_date, :parcel_id, :transaction_type, 
                          :payment_method, :check_number, :amount_paid, :balance_remaining, 
                          :payment_period, :installment_number, :notes)
            """, reversal_data)

            self.update_parcel_status(row['parcel_id'], 'UNPAID')
            self.conn.commit()
            self.log_action("NSF_REVERSAL", f"Reversed transaction {original_transaction_id}")
            print(f"NSF Reversal processed for Transaction {original_transaction_id}")

        except Exception as e:
            self.conn.rollback()
            raise e

    def update_parcel_info(self, parcel_id, new_name=None, new_address=None):
        """Updates parcel owner name or address and logs the change."""
        # Assume connection is already open by caller
        try:
            row = self.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id = ?", (parcel_id,)).fetchone()
            if not row:
                raise ValueError(f"Parcel {parcel_id} not found.")

            if new_name:
                old_name = row['owner_name']
                self.conn.execute("UPDATE tax_duplicate SET owner_name = ? WHERE parcel_id = ?", (new_name, parcel_id))
                self.log_db_change("tax_duplicate", parcel_id, "UPDATE", "owner_name", old_name, new_name)
                print(f"Updated Name: {old_name} -> {new_name}")

            if new_address:
                old_addr = row['mailing_address']
                self.conn.execute("UPDATE tax_duplicate SET mailing_address = ? WHERE parcel_id = ?", (new_address, parcel_id))
                self.log_db_change("tax_duplicate", parcel_id, "UPDATE", "mailing_address", old_addr, new_address)
                print(f"Updated Address: {old_addr} -> {new_address}")

            self.conn.commit()
            self.log_action("UPDATE_PARCEL", f"Updated info for {parcel_id}")
            print(f"Parcel {parcel_id} updated successfully.")
        except Exception as e:
            self.conn.rollback()
            raise e

    def add_interim_parcel(self, parcel_data):
        """Adds a new Interim parcel to the duplicate."""
        # Check if already exists
        # Assume connection is already open by caller
        try:
            row = self.conn.execute("SELECT * FROM tax_duplicate WHERE parcel_id = ?", (parcel_data['parcel_id'],)).fetchone()
            if row:
                raise ValueError(f"Parcel {parcel_data['parcel_id']} already exists.")

            query = """
            INSERT INTO tax_duplicate (
                parcel_id, owner_name, property_address, mailing_address, bill_number, 
                assessment_value, face_tax_amount, discount_amount, penalty_amount,
                tax_type, bill_issue_date, is_interim, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'UNPAID')
            """
            
            # Calculate financials if passed 0, or trust user input. 
            # Ideally, calculator should do this, but DB layer takes raw data.
            
            self.conn.execute(query, (
                parcel_data['parcel_id'],
                parcel_data['owner_name'],
                parcel_data['property_address'],
                parcel_data.get('mailing_address', parcel_data['property_address']),
                parcel_data['bill_number'],
                parcel_data['assessment_value'],
                parcel_data['face_tax_amount'],
                parcel_data['discount_amount'],
                parcel_data['penalty_amount'],
                parcel_data.get('tax_type', 'Real Estate'),
                parcel_data['bill_issue_date']
            ))
            
            self.conn.commit()
            self.log_action("ADD_INTERIM", f"Added Interim Parcel {parcel_data['parcel_id']}")
            print(f"Interim Parcel {parcel_data['parcel_id']} added successfully.")
            
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_parcel_details(self, search_term):
        """
        Fetches full details for a parcel, including transaction history.
        search_term: can be a Parcel ID or part of an Owner Name.
        """
        # Assume connection is already open by caller
        try:
            # 1. Find the Parcel Record
            query = "SELECT * FROM tax_duplicate WHERE parcel_id = ? OR owner_name LIKE ?"
            row = self.conn.execute(query, (search_term, f"%{search_term}%")).fetchone()
            
            if not row:
                return None

            parcel_data = dict(row)
            parcel_id = parcel_data['parcel_id']

            # 2. Find Associated Transactions
            tx_query = "SELECT * FROM transactions WHERE parcel_id = ? ORDER BY date_received ASC"
            tx_rows = self.conn.execute(tx_query, (parcel_id,)).fetchall()
            transactions = [dict(tx) for tx in tx_rows]
            
            return {
                'parcel': parcel_data,
                'transactions': transactions
            }
        finally:
            # Do NOT disconnect here; connection is managed by caller
            pass
