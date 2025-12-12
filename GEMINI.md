# Tax Commander: Tioga Township Tax Collection System

**Version:** 1.1.0 (Production Ready)
**Role:** Tax Collector Operations Platform
**Owner:** Charles E. Forsyth III, Tax Collector

## Project Overview

**Tax Commander** is a specialized Command Line Interface (CLI) system designed to automate, audit, and secure the tax collection process for Tioga Township. It replaces manual spreadsheets with a database-backed, audit-proof engine that handles calculations, receipts, and state-mandated reporting (PA Act 48 compliant).

### Key Features
*   **Audit-Proof:** Every transaction is logged and immutable.
*   **Strict Compliance:** Enforces exact payments (Discount/Face/Penalty) and rejects invalid amounts.
*   **Automated Paperwork:** Generates PDF Bills, Certificates of Payment (Receipts), Deposit Slips, and Monthly Reports.
*   **Payment Processing:** Supports manual entry and simulated check "ingestion" (image processing).
*   **Printing:** Integrated support for batch printing bills and mailing labels via CUPS.

## Architecture & Codebase

The project is a modular Python CLI application using SQLite for data persistence.

### Key Files
*   `tax_commander.py`: Main entry point and CLI command router.
*   `config.yaml`: Central configuration for contact info, millage rates, and file paths.
*   `schema.sql`: Database schema defining the `tax_duplicate`, `transactions`, `remittances`, and audit logs.
*   `biller.py`: Generates PDF tax bills using `reportlab`.
*   `ingest.py`: Handles "ingestion" of check images (currently simulated) to extract payment details.
*   `printer.py`: Manages printer interactions (CUPS) and Avery label generation.
*   `reporter.py`: Generates monthly/yearly financial reports (CSV/Excel).
*   `calculator.py`: Logic for calculating tax periods and amounts (Discount/Face/Penalty).
*   `db_manager.py`: Database connection and transaction management.

## Setup & Configuration

### Prerequisites
*   Python 3.12+
*   Dependencies: `pip install -r requirements.txt` (includes `pandas`, `reportlab`, `pyyaml`, `qrcode[pil]`, etc.)

### Configuration (`config.yaml`)
Review and update `config.yaml` before operations:
*   **Organization:** Contact details, address, and collector name.
*   **Financial:** Millage rates and bank account numbers.
*   **System:** File paths for DB, logs, and output directories.

### Initialization
To start fresh for a new tax year:
```bash
# Initialize the database schema
python3 tax_commander.py init-db

# Import the Tax Duplicate (CSV from County)
python3 tax_commander.py import-duplicate path/to/county_file.csv
```

## Daily Operations

### Recording Payments
*   **Manual Entry:**
    ```bash
    python3 tax_commander.py pay --parcel <PARCEL_ID> --amount <AMOUNT> --date <POSTMARK_DATE> --check <CHECK_NUM>
    ```
*   **Image Ingestion (Simulated):**
    ```bash
    python3 tax_commander.py ingest <IMAGE_PATH>
    ```

### Generating Documents
*   **Receipts:** `python3 tax_commander.py receipt <TRANSACTION_ID>`
*   **Deposit Slips:** `python3 tax_commander.py deposit-slip <YYYY-MM-DD>`
*   **Tax Bills:** `python3 tax_commander.py generate-bills --type Township_County`

## Reporting & Administration

*   **Monthly Report:** `python3 tax_commander.py report --month <MM> --year <YYYY>`
*   **Supervisor Dashboard:** `python3 tax_commander.py dashboard` (Web view)
*   **Close Month:** `python3 tax_commander.py close-month --month <MM> --year <YYYY>`
*   **Audit Log:** `python3 tax_commander.py audit`
*   **Turnover Report:** `python3 tax_commander.py turnover-report` (End of year)

## Development Conventions

*   **Database:** All changes must be atomic. Use `DBManager` for connections.
*   **Logging:** All critical actions are logged to `tax_commander.log` and the `system_log` table.
*   **PDF Generation:** Use `reportlab` for high-quality, printable outputs.
*   **Safety:** The `transactions` table is the source of truth. Never manually delete records; use reversal transactions if needed.
