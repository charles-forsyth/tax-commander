import csv
import os

def generate_sample_csv(filename="sample_duplicate.csv"):
    """
    Generates a sample tax duplicate CSV file for testing and demonstration.
    """
    headers = [
        "parcel_id", "owner_name", "property_address", "mailing_address", "bill_number",
        "assessment_value", "face_tax_amount", "discount_amount", "penalty_amount",
        "tax_type", "bill_issue_date", "is_installment_plan"
    ]
    
    records = []
    
    # 1. Standard Residents (001-090)
    for i in range(1, 91):
        assessment = 100000
        face = 450.00
        discount = 441.00 # 2% off
        penalty = 495.00 # 10% add
        prop_address = f"{i} Main St"
        
        records.append({
            "parcel_id": f"P-{i:03d}",
            "owner_name": f"Resident {i}",
            "property_address": prop_address,
            "mailing_address": prop_address, # Default to property address
            "bill_number": f"B{2025000+i}",
            "assessment_value": assessment,
            "face_tax_amount": face,
            "discount_amount": discount,
            "penalty_amount": penalty,
            "tax_type": "Real Estate",
            "bill_issue_date": "2025-03-01",
            "is_installment_plan": 0
        })

    # Special cases for mailing address
    records[0]["mailing_address"] = "123 P.O. Box, Anytown PA 16901" # P-001 has different mailing
    records[1]["mailing_address"] = "456 Rental Ave, City PA 17001" # P-002 has different mailing

    # 2. Installment Payers (091-095)
    for i in range(91, 96):
        prop_address = f"{i} Main St"
        records.append({
            "parcel_id": f"P-{i:03d}",
            "owner_name": f"Installment User {i}",
            "property_address": prop_address,
            "mailing_address": prop_address,
            "bill_number": f"B{2025000+i}",
            "assessment_value": 100000,
            "face_tax_amount": 450.00,
            "discount_amount": 441.00,
            "penalty_amount": 495.00,
            "tax_type": "Real Estate",
            "bill_issue_date": "2025-03-01",
            "is_installment_plan": 1
        })

    # 3. Interims (096-097) - Issued Later (July 1)
    for i in range(96, 98):
        prop_address = f"{i} New Rd"
        records.append({
            "parcel_id": f"P-{i:03d}",
            "owner_name": f"New Build {i}",
            "property_address": prop_address,
            "mailing_address": prop_address,
            "bill_number": f"B{2025000+i}",
            "assessment_value": 50000,
            "face_tax_amount": 225.00,
            "discount_amount": 220.50,
            "penalty_amount": 247.50,
            "tax_type": "Real Estate",
            "bill_issue_date": "2025-07-01", # Different Issue Date!
            "is_installment_plan": 0
        })

    # 4. Exoneration Candidate (098)
    prop_address = "98 Poor House Ln"
    records.append({
        "parcel_id": "P-098",
        "owner_name": "Indigent Person",
        "property_address": prop_address,
        "mailing_address": prop_address,
        "bill_number": "B2025098",
        "assessment_value": 10000,
        "face_tax_amount": 45.00,
        "discount_amount": 44.10,
        "penalty_amount": 49.50,
        "tax_type": "Per Capita",
        "bill_issue_date": "2025-03-01",
        "is_installment_plan": 0
    })
    
    # 5. NSF Candidate (099)
    prop_address = "99 Check Rd"
    records.append({
        "parcel_id": "P-099",
        "owner_name": "Bouncy Bob",
        "property_address": prop_address,
        "mailing_address": prop_address,
        "bill_number": "B2025099",
        "assessment_value": 100000,
        "face_tax_amount": 450.00,
        "discount_amount": 441.00,
        "penalty_amount": 495.00,
        "tax_type": "Real Estate",
        "bill_issue_date": "2025-03-01",
        "is_installment_plan": 0
    })

    # Write to CSV
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)
    
    return os.path.abspath(filename)
