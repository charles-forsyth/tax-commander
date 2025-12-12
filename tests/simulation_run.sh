#!/bin/bash

# Simulation Run: "The Gauntlet"
# Tests the Tax Commander against the edge cases defined in the plan.

DB_FILE="tioga_tax.db"
CMD="tax-commander"
export TAX_COMMANDER_TEST_MODE=1

echo "=========================================="
echo "PHASE 0: FLIGHT SIMULATOR STARTING"
echo "=========================================="

# 1. Clean Slate
echo "[1/6] Cleaning up old simulation data..."
rm -f $DB_FILE
rm -f dummy_duplicate.csv
rm -rf tax_bills # Clean up tax bills folder
rm -rf receipts # Clean up receipts folder
rm -f header_logo.png # Clean up extracted logo

# 2. Setup
echo "[2/6] initializing Database..."
$CMD init-db

echo "[3/6] Generating Dummy Data..."
python3 tests/generate_dummy_data.py

echo "[4/6] Importing Duplicate..."
$CMD import-duplicate dummy_duplicate.csv

echo "=========================================="
echo "SCENARIO TESTING"
echo "=========================================="

# Scenario 1: The Good Citizen (Exact Match - Discount)
# Bill Issued: Mar 1. Discount Ends: Apr 30.
# Paying on Apr 15. Expected: $441.00
echo -n "Test 1: Discount Exact Match (P-001)... "
$CMD pay --parcel P-001 --amount 441.00 --date 2025-04-15 
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 2: The Procrastinator (Exact Match - Face)
# Face Period: May 1 - Jun 30.
# Paying on May 15. Expected: $450.00
echo -n "Test 2: Face Exact Match (P-002)... "
$CMD pay --parcel P-002 --amount 450.00 --date 2025-05-15 
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 3: The Forgetful One (Exact Match - Penalty)
# Penalty Period: Jul 1 onwards.
# Paying on Jul 15. Expected: $495.00
echo -n "Test 3: Penalty Exact Match (P-003)... "
$CMD pay --parcel P-003 --amount 495.00 --date 2025-07-15 
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 4: The Penny Short (MUST FAIL)
# P-004 owes $441.00 (Discount). Pays $440.99.
echo -n "Test 4: Penny Short Rejection (P-004)... "
$CMD pay --parcel P-004 --amount 440.99 --date 2025-04-15
if [ $? -eq 1 ]; then echo "PASS (Correctly Rejected)"; else echo "FAIL (Accepted Incorrect Amount)"; fi

# Scenario 5: The Overpayer (MUST FAIL)
# P-005 owes $441.00. Pays $450.00 (Forgot discount?).
echo -n "Test 5: Overpayment Rejection (P-005)... "
$CMD pay --parcel P-005 --amount 450.00 --date 2025-04-15 
if [ $? -eq 1 ]; then echo "PASS (Correctly Rejected)"; else echo "FAIL (Accepted Overpayment)"; fi

echo "=========================================="


# Scenario 6: Interim Bill Discount Logic (P-096)
# Issued Jul 1. Discount ends Aug 31.
# Paying Aug 15. Expected: $220.50 (Discount)
echo -n "Test 6: Interim Bill Discount Logic (P-096)... "
$CMD pay --parcel P-096 --amount 220.50 --date 2025-08-15 
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 7: Installment Payment (P-091 - 1st Installment)
# P-091 has face tax of $450.00, so 1st installment is $150.00.
echo -n "Test 7: Installment Payment (P-091)... "
$CMD pay --parcel P-091 --amount 150.00 --date 2025-05-15 --installment-num 1
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 8: Image Ingestion (P-010 - Simulated Gemini Input)
# Simulates processing an image and user confirming extracted data.
# The ingest.py has a hardcoded mock for P-010, Check 1001, Amount 441.00, Date 2025-04-20.
# This should PASS as it's a valid discount payment for P-010.
echo -n "Test 8: Image Ingestion (P-010)... "
# We need to simulate user input for the ingest command. For now, we'll just run it
# and rely on the internal mock to pass.
{ echo "yes"; } | $CMD ingest dummy_image.jpg 
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi



echo "=========================================="
echo "PHASE 3: PAPERWORK & REPORTING"
echo "=========================================="

# Scenario 9: Generate Receipt (Transaction 1 - P-001)
echo -n "Test 9: Generate Receipt (Tx 1)... "
$CMD receipt 1
if [ -f "receipts/Receipt_P-001_1.txt" ]; then 
    echo "Text Receipt saved to receipts/Receipt_P-001_1.txt"
    if [ -f "receipts/Receipt_P-001_1.pdf" ]; then
        echo "✅ Formal PDF Certificate saved to: receipts/Receipt_P-001_1.pdf"
        echo "PASS"
    else
        echo "FAIL (PDF not found)"
    fi
else 
    echo "FAIL (File not found)" 
fi

# Scenario 10: Deposit Slip (For Today's Physical Receipt Date)
echo -n "Test 10: Deposit Slip (2025-04-20)... "
$CMD deposit-slip "2025-04-20"
if [ -f "Deposit_Slip_2025-04-20.txt" ]; then echo "PASS"; else echo "FAIL (File not found)"; fi

# Scenario 11: Monthly Report & Close (April 2025)
MONTH="04"
YEAR="2025"
echo -n "Test 11: Monthly Report & Close ($MONTH/$YEAR)... "
$CMD report --month $MONTH --year $YEAR
if [ -f "Monthly_Report_${YEAR}_${MONTH}.csv" ]; then 
    # Now Close
    $CMD close-month --month $MONTH --year $YEAR
    echo "PASS"
else 
    echo "FAIL (Report not generated)"
fi

# Scenario 13: Exoneration (P-098 - Indigent)
echo -n "Test 13: Exoneration (P-098)... "
$CMD exonerate --parcel P-098 --amount 45.00 --date 2025-05-20 --reason "Indigent"
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 14: NSF Reversal (Transaction 2 - P-002)
# Reversing the payment made in Test 2.
echo -n "Test 14: NSF Reversal (Tx 2)... "
$CMD nsf 2
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 15: Closed Month Rejection
# Attempt to add a new payment to April 2025 (which was closed in Test 11).
echo -n "Test 15: Closed Month Rejection (P-001 in 04/2025)... "
$CMD pay --parcel P-001 --amount 10.00 --date 2025-04-01 --check 9999
if [ $? -eq 1 ]; then echo "PASS (Correctly Rejected)"; else echo "FAIL (Accepted into closed month)"; fi

# Scenario 16: Installment Late Payment Rejection
# Attempt to pay an installment for P-091 during the Penalty Period (e.g., July).
# P-091 has bill issue date 2025-03-01. Penalty period starts July 1.
echo -n "Test 16: Installment Late Rejection (P-091 in 07/2025)... "
$CMD pay --parcel P-091 --amount 150.00 --date 2025-07-15 --installment-num 1
if [ $? -eq 1 ]; then echo "PASS (Correctly Rejected)"; else echo "FAIL (Accepted late installment)"; fi

# Scenario 17: Return List (Unpaid Taxes)
echo -n "Test 17: Return List Generation... "
$CMD return-list 
# Filename has timestamp, check for any Return_List*.csv
if ls Return_List_*.csv &> /dev/null; then echo "PASS"; else echo "FAIL"; fi

# Scenario 18: Audit Log Check
echo -n "Test 18: Audit Log Check... "
$CMD audit --limit 5 > /dev/null
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 19: Generate Tax Bills (Township_County)
CURRENT_MONTH_YEAR=$(date +%Y-%m)
EXPECTED_BILL_DIR="tax_bills/${CURRENT_MONTH_YEAR}_Township_County"
# Corrected prefix: Township_County_P-001_Bill_2025-11.pdf
EXPECTED_BILL_FILE_PATTERN="Township_County_P-*_Bill_${CURRENT_MONTH_YEAR}.pdf"

echo -n "Test 19: Generate Tax Bills (Township_County)... "
$CMD generate-bills --type Township_County
if [ $? -eq 0 ] && [ -d "$EXPECTED_BILL_DIR" ] && [ $(ls "${EXPECTED_BILL_DIR}"/${EXPECTED_BILL_FILE_PATTERN} | wc -l) -gt 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 20: Status Report
echo -n "Test 20: Status Report... "
$CMD status > /dev/null
# Check if a Status Report file exists (date pattern YYYY-MM-DD)
if ls Status_Report_*.md &> /dev/null; then echo "PASS"; else echo "FAIL"; fi

# Scenario 21: Export Mailing Labels
echo -n "Test 21: Export Mailing Labels... "
$CMD export-labels > /dev/null
if ls Mailing_Labels_*.csv &> /dev/null; then echo "PASS"; else echo "FAIL"; fi

# Scenario 22: Reprint Bill (P-001)
echo -n "Test 22: Reprint Bill (P-001)... "
# Reprints usually go to tax_bills/reprints/
$CMD reprint-bill --parcel P-001 --type Township_County > /dev/null
if [ -f "tax_bills/reprints/Township_County_P-001_Bill_REPRINT.pdf" ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 23: Turnover Report (Lien List)
CURRENT_DATE=$(date +%Y-%m-%d)
echo -n "Test 23: Turnover Report... "
$CMD turnover-report > /dev/null
if [ -f "Turnover_Report_${CURRENT_DATE}.xlsx" ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 24: Update Parcel (Address Change)
echo -n "Test 24: Update Parcel (P-005 Address Change)... "
$CMD update-parcel --parcel P-005 --address "999 New Address Ln, Florida" > /dev/null
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 25: Installment 2 & 3 (P-091 - Completing Payments)
echo -n "Test 25: Installment 2 & 3 (P-091)... "
# Pay Installment 2 (Due by Face end, e.g. June/July, usually flexible if accepted)
$CMD pay --parcel P-091 --amount 150.00 --date 2025-06-15 --installment-num 2 > /dev/null
# Pay Installment 3 (Final)
$CMD pay --parcel P-091 --amount 150.00 --date 2025-07-15 --installment-num 3 > /dev/null
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 26: Add Interim Parcel (P-INT-001)
echo -n "Test 26: Add Interim Parcel (P-INT-001)... "
$CMD add-interim \
    --parcel P-INT-001 \
    --name "New Homeowner" \
    --address "789 New Construction Blvd, Tioga, PA 16946" \
    --assessment 50000.00 \
    --face 500.00 \
    --discount 490.00 \
    --penalty 550.00 \
    --issue-date 2025-07-01 > /dev/null
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 27: Settlement Report
echo -n "Test 27: Settlement Report... "
$CMD settlement > /dev/null
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 28: Lookup Command (P-001)
echo "Test 28: Lookup Command (P-001)... "
$CMD lookup P-001 
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 29: Lookup Complex Case (P-091 - Installments)
echo "Test 29: Lookup Complex Case (P-091)... "
$CMD lookup P-091
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 30: Lookup Unpaid/Rejected Case (P-004)
echo "Test 30: Lookup Unpaid Case (P-004)... "
$CMD lookup P-004
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi

# Scenario 31: Rejected Payment Logged & Visible (P-005 - Overpayment)
# P-005 attempts to overpay, which will be rejected but now logged.
echo "Test 31: Rejected Payment Logged & Visible (P-005)... "
$CMD pay --parcel P-005 --amount 450.00 --date 2025-04-15 
if [ $? -eq 1 ]; then # Expect rejection (exit code 1)
    echo "(Payment rejected as expected)"
    $CMD lookup P-005
    if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL (Lookup failed)"; fi
else 
    echo "FAIL (Payment unexpectedly accepted)"
fi

echo "=========================================="
echo "SIMULATION COMPLETE"

