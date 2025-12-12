import json
import os
from datetime import datetime
from .db_manager import DBManager

class IngestManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def process_image(self, image_path):
        """
        Simulates processing an image (e.g., check) using a Gemini-like model
        to extract payment details.
        
        In a real scenario, this would involve:
        1. Loading the image.
        2. Sending to Gemini API with a prompt.
        3. Parsing the JSON response.

        For this simulation, we will prompt the user for the extracted data.
        """
        print(f"\n--- Simulating image processing for {image_path} ---")
        print("Please provide the extracted information (simulating Gemini output):")
        
        # --- MOCK GEMINI OUTPUT for demonstration ---
        # In a real scenario, this data would come from the Gemini API call
        # For now, we'll use a hardcoded example or prompt the user.

        # Example: Simulating a payment for P-010
        extracted_data = {
            "check_number": "1001",
            "amount": "441.00",
            "postmark_date": "2025-04-20",
            "payer_name": "Simulated Payer",
            "payer_address": "10 Main St",
            "found_parcel_id": "P-010" # This would be from fuzzy match or direct OCR
        }
        # --- END MOCK ---

        # Simulate user confirmation/override
        confirmed_data = self._confirm_extracted_data(extracted_data)
        if not confirmed_data:
            return None # User cancelled

        # Fuzzy match and duplicate protection logic will be here, after initial extraction
        # For now, we'll assume the 'found_parcel_id' is correct for the mock.
        parcel_id = confirmed_data["found_parcel_id"]

        # Check for duplicates
        if self._check_for_duplicate_payment(parcel_id, confirmed_data["check_number"], float(confirmed_data["amount"])):
            print("WARNING: Potential duplicate payment detected! Review manually.")
            if not input("Do you wish to proceed anyway? (yes/no): ").lower() == 'yes':
                return None

        return confirmed_data

    def _confirm_extracted_data(self, data):
        """
        Presents extracted data to the user for confirmation and allows overrides.
        """
        print("Extracted Data:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        
        confirm = input("Is this data correct? (yes/no/edit): ").lower()
        if confirm == 'yes':
            return data
        elif confirm == 'edit':
            edited_data = data.copy()
            for key in data:
                new_value = input(f"Enter new value for {key} (or press Enter to keep '{data[key]}'): ")
                if new_value:
                    edited_data[key] = new_value
            return edited_data
        else:
            return None

    def _check_for_duplicate_payment(self, parcel_id, check_number, amount):
        """
        Checks if a transaction with the same check number and amount for the
        same parcel_id already exists.
        """
        self.db.connect()
        cursor = self.db.conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE parcel_id = ? AND check_number = ? AND amount_paid = ?
        """, (parcel_id, check_number, amount))
        is_duplicate = cursor.fetchone()[0] > 0
        self.db.disconnect()
        return is_duplicate

    def _fuzzy_match_parcel(self, payer_name, payer_address):
        """
        Simulates fuzzy matching to find a parcel ID based on payer info.
        In a real system, this would query the tax_duplicate table.
        For now, we'll return a hardcoded value for demonstration.
        """
        # Placeholder for actual fuzzy matching logic
        # For simulation, assume we found 'P-010'
        return "P-010"

# Example usage (for testing this module directly)
if __name__ == "__main__":
    # This part would typically be called from tax_commander.py
    db_manager = DBManager()
    ingest_manager = IngestManager(db_manager)
    
    # Generate some dummy data for the DB if it doesn't exist
    if not os.path.exists("tioga_tax.db"): # Check if DB exists, if not, generate dummy data for testing
        print("No database found. Generating dummy data for testing ingest_manager.")
        # You'd typically run generate_dummy_data.py and import it here
        # For a simple test, let's add one record manually
        db_manager.connect()
        db_manager.conn.execute("""
            INSERT OR IGNORE INTO tax_duplicate 
            (parcel_id, owner_name, property_address, bill_number, 
             assessment_value, face_tax_amount, discount_amount, penalty_amount,
             tax_type, bill_issue_date, is_installment_plan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "P-010", "Simulated Payer", "10 Main St", "B2025010",
            100000.0, 450.00, 441.00, 495.00,
            "Real Estate", "2025-03-01", 0
        ))
        db_manager.conn.commit()
        db_manager.disconnect()

    extracted_info = ingest_manager.process_image("path/to/check_image.jpg")
    if extracted_info:
        print("Ingestion successful!")
        print(extracted_info)
    else:
        print("Ingestion cancelled or failed.")
