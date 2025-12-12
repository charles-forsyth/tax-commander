# 🦅 Tax Commander

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-production--ready-green.svg)]()

**Tax Commander** is a professional-grade, audit-proof tax collection system designed for Pennsylvania Municipal Tax Collectors. It replaces fragile spreadsheets with a robust CLI tool that enforces strict compliance with PA Act 48 (Discount/Face/Penalty periods), automates paperwork, and provides real-time financial transparency.

> **Role:** Operations Platform for Tioga Township  
> **Owner:** Charles E. Forsyth III, Tax Collector

---

## 🚀 Key Features

*   **🛡️ Audit-Proof Ledger:** Immutable transaction logging. Every penny is tracked; nothing can be "accidentally" deleted.
*   **⚖️ Strict Compliance:** automatically calculates and enforces Discount (2%), Face, and Penalty (10%) periods based on postmark dates.
*   **📄 Automated Documents:** Generates professional PDF Tax Bills (with QR codes), Certificates of Payment (Receipts), and Deposit Slips.
*   **📊 Monthly Reporting:** One-click generation of DCED-compliant Monthly Remittance Reports and check-writing advice.
*   **📈 Supervisor Dashboard:** Built-in web interface for real-time visualization of collection progress.
*   **🖨️ Batch Printing:** Integrated CUPS support for mass printing of bills and Avery 5160 mailing labels.

---

## 📥 Installation

Tax Commander is a Python package managed with `uv`.

### Option 1: Global Installation (Recommended)
Install it once and run it from anywhere on your system.

```bash
# Using uv (Recommended)
uv tool install git+ssh://git@github.com/charles-forsyth/tax-commander.git

# Or using pip
pip install git+ssh://git@github.com/charles-forsyth/tax-commander.git
```

### Option 2: Development Setup
```bash
git clone git@github.com:charles-forsyth/tax-commander.git
cd tax-commander
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## ⚙️ Configuration

1.  **Create Config Directory:**
    ```bash
    mkdir -p ~/.config/tax-commander
    ```
2.  **Copy Template:**
    Download the example config and save it to the folder above.
    ```bash
    curl -o ~/.config/tax-commander/config.yaml https://raw.githubusercontent.com/charles-forsyth/tax-commander/master/config.yaml.example
    ```
3.  **Edit Details:**
    Open `config.yaml` and set your:
    *   **Millage Rates** (Township, County, School)
    *   **Bank Account Numbers**
    *   **Contact Information**

---

## 📖 Usage Guide

### Initial Setup
Start a new tax year by initializing the database and importing the "duplicate" (the master list of taxable properties from the County).
```bash
tax-commander init-db
tax-commander import-duplicate path/to/county_export.csv
```

### Daily Workflow
**1. Record a Payment**
```bash
tax-commander pay --parcel P-001 --amount 441.00 --date 2025-04-15
```
*   *Note: The system rejects payments that don't match the exact amount due for the given date.*

**2. Generate Receipt**
```bash
tax-commander receipt <TRANSACTION_ID>
```

**3. Create Deposit Slip**
```bash
tax-commander deposit-slip 2025-04-20
```

### Monthly Workflow
**1. View Dashboard**
```bash
tax-commander dashboard
```

**2. Close the Month & Generate Reports**
```bash
tax-commander report --month 04 --year 2025
tax-commander close-month --month 04 --year 2025
```

---

## 🧪 Testing
The project includes "The Gauntlet"—a simulation script that runs the system through an entire tax year of edge cases (interim bills, penalties, partial payments, exonerations).

```bash
bash tests/simulation_run.sh
```

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).