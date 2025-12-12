from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class TaxCalculator:
    def __init__(self, default_issue_date="2025-03-01"):
        self.default_issue_date = default_issue_date

    def determine_period(self, postmark_date_str, bill_issue_date_str=None):
        """
        Returns 'DISCOUNT', 'FACE', or 'PENALTY' based on date.
        postmark_date_str: 'YYYY-MM-DD'
        bill_issue_date_str: 'YYYY-MM-DD' (Optional, defaults to March 1)
        """
        if not bill_issue_date_str:
            bill_issue_date_str = self.default_issue_date

        issue_date = datetime.strptime(bill_issue_date_str, "%Y-%m-%d").date()
        postmark = datetime.strptime(postmark_date_str, "%Y-%m-%d").date()
        
        # Calculate Deadlines relative to THIS bill's issue date
        discount_end = issue_date + relativedelta(months=2) - timedelta(days=1)
        face_end = issue_date + relativedelta(months=4) - timedelta(days=1)
        
        if postmark <= discount_end:
            return 'DISCOUNT'
        elif postmark <= face_end:
            return 'FACE'
        else:
            return 'PENALTY'

    def get_expected_amount(self, period, duplicate_record):
        """
        Returns the exact expected amount for the period.
        duplicate_record: dict/row from tax_duplicate table
        """
        if period == 'DISCOUNT':
            return duplicate_record['discount_amount']
        elif period == 'FACE':
            return duplicate_record['face_tax_amount']
        else: # PENALTY
            # If penalty amount is pre-calculated in DB, use it. 
            # Otherwise, 10% penalty calculation logic could go here.
            # For this system, we rely on the DB 'penalty_amount' field.
            return duplicate_record['penalty_amount']

    def validate_payment(self, duplicate_record, amount_tendered, postmark_date_str, installment_num=None):
        """
        Strict validation of payment amount, including installment payments.
        Returns: (is_valid, message, status_code)
        """
        issue_date = duplicate_record['bill_issue_date']
        period = self.determine_period(postmark_date_str, issue_date)
        expected_full_amount = self.get_expected_amount(period, duplicate_record)
        
        # 1. Check for Exact Full Payment (Discount, Face, or Penalty)
        if round(amount_tendered - expected_full_amount, 2) == 0:
            return (True, "Exact Match (Full Payment)", "ACCEPTED_FULL")

        # 2. Handle Installment Payments
        if duplicate_record['is_installment_plan']:
            # If it's the PENALTY period, installments are typically no longer valid at face value,
            # UNLESS it is Installment 2 or 3 which have later due dates.
            # For simplicity, we allow Inst 2/3 in Penalty period (assuming they haven't missed their specific deadline).
            if period == 'PENALTY' and (installment_num is None or installment_num == 1):
                return (False, "Installment plan invalid during Penalty Period. Full penalty amount required.", "REJECTED_INSTALLMENT_LATE")

            # For simplicity, assume 3 equal installments based on Face amount
            expected_installment_amount = round(duplicate_record['face_tax_amount'] / 3, 2)

            # Check if tendered amount matches an exact installment amount
            if round(amount_tendered - expected_installment_amount, 2) == 0:
                return (True, f"Exact Match (Installment {installment_num or 1})", "ACCEPTED_INSTALLMENT")
            
            # Also check for Penalty Installment (10% on the installment amount) if late
            expected_installment_penalty = round(expected_installment_amount * 1.10, 2)
            if round(amount_tendered - expected_installment_penalty, 2) == 0:
                 return (True, f"Exact Match (Penalty Installment {installment_num})", "ACCEPTED_INSTALLMENT_PENALTY")
            
        # 3. Handle Overpayments
        if amount_tendered > expected_full_amount:
            diff = round(amount_tendered - expected_full_amount, 2)
            return (False, f"OVERPAYMENT of ${diff}. Do not deposit. Issue Refund/Return Check.", "REJECTED_OVER")
        
        # 4. Handle Underpayments (Penny Short or invalid partial)
        diff = round(expected_full_amount - amount_tendered, 2)
        return (False, f"UNDERPAYMENT of ${diff}. Exact amount required or valid installment.", "REJECTED_UNDER")
