import json
import os
import google.generativeai as genai
import PIL.Image
from datetime import datetime
from .db_manager import DBManager

class IngestManager:
    def __init__(self, db_manager, config):
        self.db = db_manager
        self.config = config
        # Load API Key from Config or Environment (Env takes precedence for security)
        self.api_key = os.environ.get('GEMINI_API_KEY') or config.get('gemini', {}).get('api_key')
        self.model_name = config.get('gemini', {}).get('model', 'gemini-3-pro-preview')

    def process_image(self, image_path):
        """
        Processes an image (check) using the configured Gemini model.
        """
        # --- TEST MODE HOOK ---
        if os.environ.get('TAX_COMMANDER_TEST_MODE'):
            print(f"🧪 TEST MODE: Simulating ingestion for {image_path}")
            return {
                "check_number": "1001",
                "amount": 441.00,
                "postmark_date": "2025-04-20",
                "payer_name": "Simulated Payer",
                "payer_address": "10 Main St",
                "found_parcel_id": "P-010"
            }
        # ----------------------

        print(f"\n--- Ingesting Image: {image_path} ---")
        
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            print("❌ Error: Gemini API Key not configured.")
            print("Please set GEMINI_API_KEY env var or update config.yaml.")
            return None

        if not os.path.exists(image_path):
            print(f"❌ Error: Image file not found at {image_path}")
            return None

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            
            img = PIL.Image.open(image_path)
            
            prompt = """
            Analyze this image of a check or payment document.
            Extract the following details into a JSON object:
            - check_number (string)
            - amount (number, no currency symbols)
            - postmark_date (string, YYYY-MM-DD format. If not visible, use today's date)
            - payer_name (string)
            - payer_address (string)
            - memo (string, often contains the Parcel ID)
            
            Only return the raw JSON string, no markdown formatting.
            """
            
            print(f"🤖 Sending to {self.model_name}...")
            response = model.generate_content([prompt, img])
            
            # Clean response (sometimes returns ```json ... ```)
            raw_text = response.text.replace('```json', '').replace('```', '').strip()
            extracted_data = json.loads(raw_text)
            
            # Add logic to find Parcel ID from memo or name
            extracted_data['found_parcel_id'] = self._find_parcel_id(extracted_data)
            
            # Confirm with user
            return self._confirm_extracted_data(extracted_data)

        except Exception as e:
            print(f"❌ AI Ingestion Failed: {e}")
            return None

    def _find_parcel_id(self, data):
        """
        Attempts to find the Parcel ID from the extracted memo or payer info.
        In a real app, this would query the DB for name matches.
        """
        memo = data.get('memo', '')
        # Simple heuristic: Look for P-XXX in memo
        if memo and 'P-' in memo:
            parts = memo.split()
            for part in parts:
                if part.startswith('P-'):
                    return part.strip()
        
        # Fallback: Ask DB for name match (Simplified for now)
        # self.db.connect()
        # ... query ...
        # self.db.disconnect()
        
        return "UNKNOWN (Please Enter)"

    def _confirm_extracted_data(self, data):
        """
        Presents extracted data to the user for confirmation and allows overrides.
        """
        print("\n📝 Extracted Data:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        
        confirm = input("\nIs this data correct? (yes/no/edit): ").lower()
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