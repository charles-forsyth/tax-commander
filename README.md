# 🦅 Tax Commander: Tioga Township Tax Collection System

**Version:** 1.1.0 (Production Ready)  
**Role:** Tax Collector Operations Platform  
**Owner:** Charles E. Forsyth III, Tax Collector

---

## 📖 Overview
**Tax Commander** is a specialized CLI (Command Line Interface) system designed to automate, audit, and secure the tax collection process for Tioga Township. It replaces manual spreadsheets with a database-backed, audit-proof engine that handles calculations, receipts, and state-mandated reporting (PA Act 48 compliant).

### Key Capabilities
*   **Audit-Proof:** Every transaction is logged. You can't "accidentally" delete money.
*   **Strict Compliance:** Enforces exact payments (Discount/Face/Penalty). Rejects "penny-short" checks automatically.
*   **Automated Paperwork:** Generates professional PDF Bills (with QR codes), Certificates of Payment (Receipts), Deposit Slips, and Monthly DCED Reports.
*   **Strategic Dashboard:** Real-time web view for Supervisor meetings.
*   **Modern Contact:** Bills include a "Scan to Email" QR code and Drop Box information.

---

## ⚙️ Setup & Configuration

### 1. Prerequisites
*   Python 3.12+
*   Dependencies: `pip install -r requirements.txt` (includes `pandas`, `reportlab`, `streamlit`, `openpyxl`, `plotly`, `qrcode[pil]`, `pymupdf`)

### 2. Configuration (`config.yaml`)
**CRITICAL:** Before processing real payments, open `config.yaml` and verify:
*   **Contact Info:** Update email, phone, and address (supports PO Box).
*   **Millage Rates:** Ensure Township, County, and School millage match the current year's resolution.
*   **Bank Accounts:** Update the "Account Number" fields for the Remittance Reports.

### 3. Initialization
If starting fresh for a new year:
```bash
python3 tax_commander.py init-db
python3 tax_commander.py import-duplicate path/to/county_file.csv
```

---

## ☀️ Daily Operations (Processing Mail)

### 1. Recording a Payment
When you open an envelope:
```bash
python3 tax_commander.py pay --parcel <PARCEL_ID> --amount <AMOUNT> --date <POSTMARK_DATE> --check <CHECK_NUM>
```
*   **Validation:** The system will reject the payment if it doesn't match the exact amount due for that date.
*   **Installments:** Use `--installment-num 1` (or 2/3).

### 2. Generating a Receipt
If a resident requests a receipt:
```bash
python3 tax_commander.py receipt <TRANSACTION_ID>
```
*   Generates a formal PDF **Certificate of Payment** in the `receipts/` folder.

### 3. Creating a Deposit Slip
Before going to the bank:
```bash
python3 tax_commander.py deposit-slip <YYYY-MM-DD>
```

### 4. Updating Parcel Info (Move/Sale)
If a resident moves or name changes:
```bash
python3 tax_commander.py update-parcel --parcel <ID> --name "New Name" --address "New Address"
```

---

## 📅 Monthly Operations (Reporting)

### 1. The "Supervisor Dashboard"
Before your monthly meeting, check your stats:
```bash
python3 tax_commander.py dashboard
```
*   Opens a web page with charts and totals.

### 2. Monthly Remittance Report
At the end of the month (e.g., April):
```bash
python3 tax_commander.py report --month 4 --year 2025
```
*   Generates `Monthly_Report_YYYY_MM.csv` and prints check-writing advice.

### 3. Closing the Month
Once reports are filed:
```bash
python3 tax_commander.py close-month --month 4 --year 2025
```

---

## 🗓️ Yearly/Special Operations

### 1. Printing Tax Bills
To generate PDF bills for mailing:
```bash
python3 tax_commander.py generate-bills --type Township_County
```
*   Outputs to `tax_bills/`. Bills include QR codes and Drop Box info.

### 2. Printing Labels
To print address labels (Avery 5160):
```bash
python3 tax_commander.py export-labels
python3 tax_commander.py print-labels --printer "Canon_Printer_Name"
```

### 3. Batch Printing Bills
To print a whole folder of bills:
```bash
python3 tax_commander.py print-bills --folder tax_bills/2025-03_Township_County/ --printer "Canon_Printer_Name"
```

### 4. End-of-Year Turnover (Lien List)
On Jan 15, generate the list for the Tax Claim Bureau:
```bash
python3 tax_commander.py turnover-report
```

---

## 🛡️ Administrative Tools

*   **Audit Log:** `python3 tax_commander.py audit`
*   **Exoneration:** `python3 tax_commander.py exonerate ...`
*   **NSF (Bounced Check):** `python3 tax_commander.py nsf <TX_ID>`
*   **List Printers:** `python3 tax_commander.py list-printers`

---

**Note:** Always backup your `tioga_tax.db` file regularly. The system automatically creates backups in `backups/` before major operations.
