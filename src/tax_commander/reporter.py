import csv
import pandas as pd
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

class TaxReporter:
    def __init__(self, db_manager, config=None):
        self.db = db_manager
        self.config = config or {}

    def generate_monthly_report(self, month, year):
        """
        Generates a summary for the DCED Monthly Report and Remittance Advice.
        """
        print(f"\n--- Monthly Report for {month}/{year} ---")
        
        # Define date range
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        # Query Transactions
        self.db.connect()
        query = """
        SELECT t.*, d.tax_type 
        FROM transactions t
        JOIN tax_duplicate d ON t.parcel_id = d.parcel_id
        WHERE t.date_received >= ? AND t.date_received < ?
        """
        df = pd.read_sql_query(query, self.db.conn, params=(start_date, end_date))
        self.db.disconnect()

        if df.empty:
            print("No transactions found for this period.")
            return

        # 1. Summarize by Tax Type and Period
        summary = df.groupby(['tax_type', 'payment_period'])['amount_paid'].sum().reset_index()
        
        print("\n[Collection Summary]")
        print(summary.to_string(index=False))

        # 2. Calculate Remittances (Simplified Logic for Phase 1)
        total_collected = df['amount_paid'].sum()
        
        re_total = df[df['tax_type'] == 'Real Estate']['amount_paid'].sum()
        pc_total = df[df['tax_type'] == 'Per Capita']['amount_paid'].sum()
        
        # Current Representative Distribution Rules (from Config)
        fin_conf = self.config.get('financial', {})
        re_conf = fin_conf.get('real_estate', {'township_share': 0.80, 'county_share': 0.15, 'school_share': 0.05})
        pc_conf = fin_conf.get('per_capita', {'township_share': 0.50, 'school_share': 0.50})

        township_re_share = re_total * re_conf.get('township_share', 0.80)
        county_re_share = re_total * re_conf.get('county_share', 0.15)
        school_re_share = re_total * re_conf.get('school_share', 0.05)

        township_pc_share = pc_total * pc_conf.get('township_share', 0.50)
        school_pc_share = pc_total * pc_conf.get('school_share', 0.50)

        # Combine shares
        total_township_remittance = township_pc_share + township_re_share
        total_county_remittance = county_re_share
        total_school_remittance = school_pc_share + school_re_share

        # Get Bank Account Details
        bank_accounts = self.config.get('bank_accounts', {})
        township_bank = bank_accounts.get('township', {'name': 'Township General Fund', 'account_number': 'N/A'})
        county_bank = bank_accounts.get('county', {'name': 'County Tax Account', 'account_number': 'N/A'})
        school_bank = bank_accounts.get('school_district', {'name': 'School District', 'account_number': 'N/A'})

        print("\n[Remittance Advice - WRITE THESE CHECKS]")
        print(f"1. {township_bank['name']}:   ${total_township_remittance:,.2f} (Acct: {township_bank['account_number']})")
        print(f"2. {county_bank['name']}:     ${total_county_remittance:,.2f} (Acct: {county_bank['account_number']})")
        print(f"3. {school_bank['name']}:  ${total_school_remittance:,.2f} (Acct: {school_bank['account_number']})")
        print(f"TOTAL REMITTED:      ${total_collected:,.2f}")

        # Add a BIG FAT WARNING for the user in the report itself:
        print("\n⚠️  **WARNING: REMITTANCE PERCENTAGES ARE ESTIMATES!**")
        print("⚠️  **UPDATE `config.yaml` WITH ACTUAL MILLAGE RATES BEFORE FIRST LIVE DEPOSIT.**\n")

        # 3. DCED Specifics (Exonerations/Returns)
        exonerations = df[df['transaction_type'] == 'EXONERATION']['amount_paid'].sum()
        returns = df[df['transaction_type'] == 'RETURN']['amount_paid'].sum()
        
        print(f"\n[DCED Report Adjustments]")
        print(f"Line 6 (Exonerations): ${exonerations:,.2f}")
        print(f"Line 7 (Returns):      ${returns:,.2f}")

        # Export to CSV for record
        filename = f"Monthly_Report_{year}_{month:02d}.csv"
        df.to_csv(filename, index=False)
        print(f"\nDetailed transaction list saved to: {filename}")

    def generate_return_list(self):
        """
        Generates list of UNPAID parcels for the County Tax Claim Bureau.
        """
        print("\n--- Generating Return List (Unpaid Taxes) ---")
        
        self.db.connect()
        query = "SELECT * FROM tax_duplicate WHERE status = 'UNPAID' OR status = 'PARTIAL'"
        df = pd.read_sql_query(query, self.db.conn)
        self.db.disconnect()

        if not df.empty:
            print("Great news! No unpaid taxes found.")
            return

        filename = f"Return_List_{datetime.now().strftime('%Y-%m-%d')}.csv"
        df.to_csv(filename, index=False)
        
        print(f"Found {len(df)} unpaid/partial records.")
        print(f"Return List saved to: {filename}")
        print("Submit this file to County Tax Claim Bureau by Jan 15 / Apr 30.")

    def generate_receipt(self, transaction_id):
        """
        Generates a text receipt and a PDF Certificate of Payment.
        """
        self.db.connect()
        query = """
        SELECT t.*, d.owner_name, d.property_address 
        FROM transactions t
        JOIN tax_duplicate d ON t.parcel_id = d.parcel_id
        WHERE t.transaction_id = ?
        """
        tx = self.db.conn.execute(query, (transaction_id,)).fetchone()
        self.db.disconnect()

        if not tx:
            print(f"Transaction {transaction_id} not found.")
            return

        # Config Values
        org = self.config.get('organization', {})
        collector_name = org.get('collector_name', 'Charles Forsyth')
        township_name = org.get('township_name', 'TIOGA TOWNSHIP')

        # Ensure receipts directory exists
        receipt_dir = "receipts"
        os.makedirs(receipt_dir, exist_ok=True)

        # 1. Text Receipt (Legacy/Log)
        receipt_text = f"""
        ========================================
        OFFICIAL TAX RECEIPT - {township_name}
        ========================================
        Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Receipt #: {tx['transaction_id']}
        
        Parcel ID:      {tx['parcel_id']}
        Owner:          {tx['owner_name']}
        Property:       {tx['property_address']}
        
        Amount Paid:    ${tx['amount_paid']:.2f}
        Payment Period: {tx['payment_period']}
        Check Number:   {tx['check_number']}
        
        Status: PA ID IN FULL (Verified)
        ========================================
        Tax Collector: {collector_name}
        """
        print(receipt_text)
        
        # Save to TXT file
        txt_filename = os.path.join(receipt_dir, f"Receipt_{tx['parcel_id']}_{tx['transaction_id']}.txt")
        with open(txt_filename, "w") as f:
            f.write(receipt_text)
        print(f"Text Receipt saved to {txt_filename}")

        # 2. PDF Certificate (Formal)
        self.generate_pdf_receipt(tx, receipt_dir)

    def generate_pdf_receipt(self, tx, output_dir):
        """Creates a formal PDF Certificate of Payment."""
        # Retrieve Config
        org = self.config.get('organization', {})
        collector_name = org.get('collector_name', 'Charles Forsyth')
        collector_title = org.get('collector_title', 'Tax Collector')
        township_name = org.get('township_name', 'TIOGA TOWNSHIP')
        city_zip = org.get('city_state_zip', 'Tioga, PA 16946')

        filename = os.path.join(output_dir, f"Receipt_{tx['parcel_id']}_{tx['transaction_id']}.pdf")
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        # --- Design ---
        c.setLineWidth(2)
        c.rect(0.5 * inch, 5.0 * inch, 7.5 * inch, 5.0 * inch) # Border for receipt area (half page)

        # Header
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, 9.5 * inch, "OFFICIAL TAX RECEIPT")
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, 9.3 * inch, f"{township_name}, {city_zip}")

        # Details
        c.setFont("Helvetica", 12)
        text_x = 1.0 * inch
        start_y = 8.5 * inch
        line_height = 0.3 * inch

        c.drawString(text_x, start_y, f"Receipt Number: {tx['transaction_id']}")
        c.drawString(text_x, start_y - line_height, f"Date Received:  {tx['date_received']}")
        c.drawString(text_x, start_y - 2*line_height, f"Parcel ID:      {tx['parcel_id']}")
        c.drawString(text_x, start_y - 3*line_height, f"Owner Name:     {tx['owner_name']}")
        c.drawString(text_x, start_y - 4*line_height, f"Property:       {tx['property_address']}")

        # Financials Box
        c.setLineWidth(1)
        c.rect(4.5 * inch, 7.0 * inch, 3.0 * inch, 1.5 * inch)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(4.7 * inch, 8.2 * inch, "PAYMENT DETAILS")
        c.setFont("Helvetica", 12)
        c.drawString(4.7 * inch, 7.9 * inch, f"Amount:   ${tx['amount_paid']:.2f}")
        c.drawString(4.7 * inch, 7.6 * inch, f"Method:   {tx['payment_method']} #{tx['check_number']}")
        c.drawString(4.7 * inch, 7.3 * inch, f"Period:   {tx['payment_period']}")

        # Footer / Signature
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(text_x, 6.0 * inch, "This certifies that the taxes for the above property have been paid in the amount shown.")
        
        c.line(4.5 * inch, 5.5 * inch, 7.5 * inch, 5.5 * inch) # Sig Line
        c.drawString(4.5 * inch, 5.3 * inch, f"{collector_name}, {collector_title}")

        # "PAID" Watermark effect
        c.saveState()
        c.translate(width/2, 7.5*inch)
        c.rotate(45)
        c.setFillColorRGB(0.9, 0.9, 0.9) # Light grey
        c.setFont("Helvetica-Bold", 100)
        c.drawCentredString(0, 0, "PAID")
        c.restoreState()

        c.save()
        print(f"✅ Formal PDF Certificate saved to: {filename}")

    def get_plain_english_reason(self, reason_code):
        """
        Translates technical rejection codes into friendly, clear language.
        """
        code = reason_code.upper()
        if "UNDERPAYMENT" in code:
            return (
                "We noticed the check amount was less than the total due. By law, we are required to collect "
                "the exact amount listed on the tax bill and cannot accept partial payments. Because this check "
                "was for a lower amount, we are unable to process it and must return it to you."
            )
        elif "OVERPAYMENT" in code:
            return (
                "We noticed the check amount was higher than the total due. Since we cannot accept extra funds "
                "or issue change from the tax account, we must return this check to you. Please simply write a "
                "new check for the exact amount shown below."
            )
        elif "INSTALLMENT" in code or "LATE" in code:
            return (
                "It appears this payment was intended for an installment plan or a previous discount period, but "
                "it arrived after the deadline. As a result, the amount due has changed. We have to return this "
                "check so you can issue a new one for the current amount."
            )
        else:
            return (
                "We are unable to process this payment as submitted. Please review the specific reason below and "
                "issue a new check for the correct amount. If you have any questions, please contact our office."
            )

    def generate_rejection_letter(self, parcel_data, attempted_amount, rejection_reason, check_number):
        """
        Generates a formal PDF letter explaining why a payment was rejected and returned.
        """
        # Retrieve Config
        org = self.config.get('organization', {})
        collector_name = org.get('collector_name', 'Tax Collector Name')
        collector_title = org.get('collector_title', 'Tax Collector')
        township_name = org.get('township_name', 'MUNICIPALITY NAME')
        city_zip = org.get('city_state_zip', 'City, State Zip')
        address = org.get('mailing_address', '123 Main St')
        
        # Output directory
        output_dir = "rejection_notices"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, f"Rejection_{parcel_data['parcel_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # --- Header ---
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, 10.0 * inch, f"{township_name.upper()} TAX OFFICE")
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, 9.8 * inch, f"{collector_name}, {collector_title}")
        c.drawCentredString(width / 2, 9.6 * inch, f"{address}, {city_zip}")
        
        c.line(1.0 * inch, 9.4 * inch, 7.5 * inch, 9.4 * inch)
        
        # --- Recipient & Date ---
        c.setFont("Helvetica", 12)
        text_x = 1.0 * inch
        current_y = 8.8 * inch
        
        c.drawString(text_x, current_y, datetime.now().strftime("%B %d, %Y"))
        current_y -= 0.5 * inch
        
        c.drawString(text_x, current_y, f"{parcel_data['owner_name']}")
        current_y -= 0.2 * inch
        c.drawString(text_x, current_y, f"{parcel_data['mailing_address']}")
        
        # --- Notice Title ---
        current_y -= 0.8 * inch
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, current_y, "NOTICE OF RETURNED PAYMENT")
        
        # --- Body Text ---
        current_y -= 0.5 * inch
        c.setFont("Helvetica", 12)
        c.drawString(text_x, current_y, f"Re: Parcel ID {parcel_data['parcel_id']} ({parcel_data['property_address']})")
        
        current_y -= 0.4 * inch
        line1 = f"We are returning your check #{check_number} in the amount of ${attempted_amount:,.2f}."
        c.drawString(text_x, current_y, line1)
        
        current_y -= 0.4 * inch # Increased spacing
        c.setFont("Helvetica-Bold", 12)
        
        # --- Text Wrapping for Rejection Reason ---
        max_width = 6.5 * inch # Width of the content area (from 1.0 inch to 7.5 inch)
        wrapped_reason = []
        line = []
        for word in rejection_reason.split(' '):
            # Temporarily join current line with new word to check width
            test_line = " ".join(line + [word])
            if c.stringWidth(test_line, "Helvetica-Bold", 12) < max_width:
                line.append(word)
            else:
                wrapped_reason.append(" ".join(line))
                line = [word]
        wrapped_reason.append(" ".join(line)) # Add the last line

        c.drawString(text_x, current_y, "REASON FOR REJECTION:")
        current_y -= 0.25 * inch # Space below title
        c.setFont("Helvetica", 11) # Slightly smaller for wrapped text
        for reason_line in wrapped_reason:
            c.drawString(text_x + 0.2*inch, current_y, reason_line)
            current_y -= 0.2 * inch # Line spacing for wrapped text
        # --- End Text Wrapping ---
        
        current_y -= 0.2 * inch # Additional space after reason block
        c.setFont("Helvetica", 12) # Revert font for next section
        
        # --- Friendly Explanation (Dynamic) ---
        friendly_explanation = self.get_plain_english_reason(rejection_reason)
        
        wrapped_explanation = []
        line = []
        for word in friendly_explanation.split(' '):
            test_line = " ".join(line + [word])
            if c.stringWidth(test_line, "Helvetica", 12) < max_width:
                line.append(word)
            else:
                wrapped_explanation.append(" ".join(line))
                line = [word]
        wrapped_explanation.append(" ".join(line))

        for expl_line in wrapped_explanation:
            c.drawString(text_x, current_y, expl_line)
            current_y -= 0.25 * inch
        # --- End Friendly Explanation ---
        
        # --- Status Card ---
        current_y -= 0.6 * inch # Gap before card
        card_height = 1.5 * inch
        card_bottom = current_y - card_height
        
        c.setLineWidth(1)
        c.rect(1.0 * inch, card_bottom, 6.5 * inch, card_height)
        
        text_start_y = current_y - 0.3 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.2 * inch, text_start_y, "CURRENT AMOUNTS DUE (Please remit EXACTLY one of the following):")
        
        c.setFont("Helvetica", 11)
        c.drawString(1.2 * inch, text_start_y - 0.3*inch, f"DISCOUNT Amount:  ${parcel_data['discount_amount']:,.2f}")
        c.drawString(1.2 * inch, text_start_y - 0.6*inch, f"FACE Amount:      ${parcel_data['face_tax_amount']:,.2f}")
        c.drawString(1.2 * inch, text_start_y - 0.9*inch, f"PENALTY Amount:   ${parcel_data['penalty_amount']:,.2f}")
        
        # --- Footer ---
        # Position relative to bottom of card
        current_y = card_bottom - 0.5 * inch
        
        c.setFont("Helvetica", 12)
        c.drawString(text_x, current_y, "Please issue a new check for the correct amount corresponding to the current date.")
        c.drawString(text_x, current_y - 0.25*inch, "If you have questions, please contact the Tax Office.")
        
        current_y -= 1.0 * inch
        c.drawString(text_x, current_y, "Sincerely,")
        c.drawString(text_x, current_y - 0.5*inch, f"{collector_name}")
        c.drawString(text_x, current_y - 0.7*inch, f"{collector_title}")
        
        c.save()
        print(f"✅ Rejection Notice PDF generated: {filename}")
        return filename

    def create_deposit_slip(self, date_str):
        """
        Generates a deposit slip for all checks received on a specific date.
        """
        print(f"\n--- Deposit Slip for {date_str} ---")
        
        self.db.connect()
        query = "SELECT * FROM transactions WHERE date_received = ? AND payment_method = 'CHECK'"
        df = pd.read_sql_query(query, self.db.conn, params=(date_str,))
        self.db.disconnect()

        if df.empty:
            print(f"No check transactions found for {date_str}.")
            return

        total = df['amount_paid'].sum()
        count = len(df)

        print(f"Total Checks: {count}")
        print(f"Total Amount: ${total:,.2f}")
        print("-" * 30)
        print(df[['check_number', 'amount_paid', 'parcel_id']].to_string(index=False))
        print("-" * 30)
        
        filename = f"Deposit_Slip_{date_str}.txt"
        with open(filename, "w") as f:
            f.write(f"DEPOSIT SLIP - {date_str}\n")
            f.write(f"Total Count: {count}\n")
            f.write(f"Total Amount: ${total:,.2f}\n")
            f.write("-" * 30 + "\n")
            f.write(df[['check_number', 'amount_paid', 'parcel_id']].to_string(index=False))
        
        print(f"Deposit slip saved to {filename}")

    def export_mailing_labels(self):
        """
        Exports a CSV file of owner names and mailing addresses for Avery 5160 labels.
        """
        print("\n--- Exporting Mailing Labels ---")
        
        self.db.connect()
        query = "SELECT owner_name, mailing_address FROM tax_duplicate"
        cursor = self.db.conn.execute(query)
        rows = cursor.fetchall()
        self.db.disconnect()

        if not rows:
            print("No records found to export.")
            return

        filename = f"Mailing_Labels_{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            # Header for Mail Merge
            writer.writerow(['Name', 'Address'])
            
            for row in rows:
                writer.writerow([row['owner_name'], row['mailing_address']])
        
        print(f"Exported {len(rows)} labels to {filename}")
        print("Use this CSV with Word/Excel Mail Merge for Avery 5160 labels.")

    def generate_turnover_report(self):
        """
        Generates the Delinquency Turnover Report (Lien List) for the Tax Claim Bureau.
        Exports to Excel (.xlsx) with specific columns.
        """
        print("\n--- Generating Delinquency Turnover Report (Lien List) ---")
        
        self.db.connect()
        # Get UNPAID or PARTIAL records
        query = "SELECT * FROM tax_duplicate WHERE status IN ('UNPAID', 'PARTIAL')"
        df = pd.read_sql_query(query, self.db.conn)
        self.db.disconnect()

        if df.empty:
            print("No delinquent taxes found to turn over.")
            return

        # Prepare Data for Bureau
        # Required: Parcel ID, Owner Name, Property Address, Tax Year, Face, Penalty, Total
        
        # Calculate Total Due (Face + Penalty) - assuming full amount for simplicity of this report
        # In reality, you'd subtract any partial payments if allowed, but for turnover, usually full amount is liened
        # unless strict partial tracking is in place. Here we use the DB amounts.
        df['Tax Year'] = datetime.now().year # Current year, or should be passed in? Assuming current cycle.
        df['Total Due'] = df['face_tax_amount'] + df['penalty_amount']

        # Select and Rename Columns
        output_df = df[[ 
            'parcel_id', 'owner_name', 'property_address', 'Tax Year', 
            'face_tax_amount', 'penalty_amount', 'Total Due'
        ]].copy()
        
        output_df.columns = [
            'Parcel ID', 'Owner Name', 'Property Address', 'Tax Year', 
            'Face Tax', 'Penalty', 'Total Amount Due'
        ]

        filename = f"Turnover_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        output_df.to_excel(filename, index=False)
        
        print(f"Turnover Report generated for {len(output_df)} parcels.")
        print(f"Saved to: {filename}")
        print("Submit this file to the County Tax Claim Bureau.")

    def generate_settlement_report(self):
        """
        Generates the Annual Settlement Report (The Balancing Act).
        """
        print("\n--- Annual Settlement Report ---")
        self.db.connect()
        
        # 1. Calculate Charges
        dup_face = self.db.conn.execute("SELECT SUM(face_tax_amount) FROM tax_duplicate WHERE is_interim=0").fetchone()[0] or 0.0
        int_face = self.db.conn.execute("SELECT SUM(face_tax_amount) FROM tax_duplicate WHERE is_interim=1").fetchone()[0] or 0.0
        
        # Discounts Allowed
        query_disc = """
        SELECT SUM(d.face_tax_amount - t.amount_paid) 
        FROM transactions t 
        JOIN tax_duplicate d ON t.parcel_id = d.parcel_id
        WHERE t.transaction_type='PAYMENT' AND t.payment_period='DISCOUNT'
        """
        discounts_allowed = self.db.conn.execute(query_disc).fetchone()[0] or 0.0
        
        # Penalties Collected (The portion ABOVE face)
        query_pen = """
        SELECT SUM(t.amount_paid - d.face_tax_amount)
        FROM transactions t
        JOIN tax_duplicate d ON t.parcel_id = d.parcel_id
        WHERE t.transaction_type='PAYMENT' AND t.payment_period='PENALTY'
        """
        penalties_collected = self.db.conn.execute(query_pen).fetchone()[0] or 0.0
        
        # Returns Face & Penalty
        ret_face = self.db.conn.execute("SELECT SUM(face_tax_amount) FROM tax_duplicate WHERE status IN ('UNPAID', 'RETURNED')").fetchone()[0] or 0.0
        ret_pen = self.db.conn.execute("SELECT SUM(penalty_amount) FROM tax_duplicate WHERE status IN ('UNPAID', 'RETURNED')").fetchone()[0] or 0.0
        
        # Total Charges (Accountability)
        # Face + Interims + Penalties Collected + Penalties Due (Returned)
        total_accountable = dup_face + int_face + penalties_collected + ret_pen
        
        # 2. Calculate Credits
        tx_df = pd.read_sql_query("SELECT * FROM transactions", self.db.conn)
        
        total_cash_collected = tx_df[tx_df['transaction_type'] == 'PAYMENT']['amount_paid'].sum() if not tx_df.empty else 0.0
        exonerations = tx_df[tx_df['transaction_type'] == 'EXONERATION']['amount_paid'].sum() if not tx_df.empty else 0.0
        
        total_credits = total_cash_collected + discounts_allowed + exonerations + ret_face + ret_pen
        
        diff = total_accountable - total_credits
        
        self.db.disconnect()
        
        print(f"{'Category':<30} | {'Amount':>12}")
        print("-" * 45)
        print(f"{'CHARGES':<30} |")
        print(f"{'  Original Duplicate (Face)':<30} | ${dup_face:,.2f}")
        print(f"{'  Interim Adds (Face)':<30} | ${int_face:,.2f}")
        print(f"{'  Penalties Collected':<30} | ${penalties_collected:,.2f}")
        print(f"{'  Penalties on Returns':<30} | ${ret_pen:,.2f}")
        print(f"{'TOTAL CHARGES':<30} | ${total_accountable:,.2f}")
        print("-" * 45)
        print(f"{'CREDITS':<30} |")
        print(f"{'  Cash Collected':<30} | ${total_cash_collected:,.2f}")
        print(f"{'  Discounts Allowed':<30} | ${discounts_allowed:,.2f}")
        print(f"{'  Exonerations':<30} | ${exonerations:,.2f}")
        print(f"{'  Returns (Face + Pen)':<30} | ${(ret_face + ret_pen):,.2f}")
        print(f"{'TOTAL CREDITS':<30} | ${total_credits:,.2f}")
        print("-" * 45)
        print(f"{'BALANCE (Should be 0.00)':<30} | ${diff:,.2f}")
        
        if abs(diff) < 0.02:
            print("\n✅ BOOKS ARE BALANCED.")
        else:
            print("\n❌ IMBALANCE DETECTED. CHECK RECORDS.")
