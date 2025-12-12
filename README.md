# 🦅 Tax Commander

[![CI Status](https://github.com/charles-forsyth/tax-commander/actions/workflows/ci.yml/badge.svg)](https://github.com/charles-forsyth/tax-commander/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **The Open-Source Operating System for PA Tax Collectors**  
> Automate bills, enforce compliance, and ingest checks with AI—all from the terminal.

---

## 📸 Screenshots

*(Screenshots coming soon)*

---

## 🚀 Why Tax Commander?

Managing municipal taxes with spreadsheets is a recipe for disaster. **Tax Commander** provides an **audit-proof**, **compliant**, and **automated** platform designed specifically for the complexities of Pennsylvania Act 48 (Discount/Face/Penalty logic).

### ✨ Features at a Glance

| Feature | Description |
| :--- | :--- |
| **🤖 AI Check Ingestion** | Take a photo of a check. **Gemini 3 Pro** extracts the amount, date, and Parcel ID automatically. |
| **🛡️ Audit-Proof Ledger** | Immutable transaction logging. Every penny is tracked. No "accidental" deletions. |
| **⚖️ Auto-Compliance** | Automatically enforces 2% Discount, Face, and 10% Penalty periods based on postmark. |
| **📄 Paperwork Automation** | Generates professional PDF **Tax Bills** (with QR codes) and **Certificates of Payment**. |
| **📊 Instant Reporting** | One-click **DCED Monthly Reports** and Remittance Advice. |
| **📈 Supervisor Dashboard** | Real-time web view for your monthly township meetings. |

---

## 📥 Installation

Tax Commander is managed with `uv` for lightning-fast installation.

```bash
# 1. Install Tool
uv tool install git+https://github.com/charles-forsyth/tax-commander.git

# 2. Initialize Config
mkdir -p ~/.config/tax-commander
curl -o ~/.config/tax-commander/config.yaml https://raw.githubusercontent.com/charles-forsyth/tax-commander/master/config.yaml.example
```

### Option 2: Development Setup
```bash
git clone https://github.com/charles-forsyth/tax-commander.git
cd tax-commander
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## 📖 Usage Guide

### 1. Initial Setup
Start a new tax year by initializing the database and importing the "duplicate" (the master list of taxable properties from the County).
```bash
tax-commander init-db
tax-commander import-duplicate path/to/county_export.csv
```

### 2. Daily Payment Processing

**Option A: Manual Entry**
Standard payment recording. The system validates the amount against the current period (Discount/Face/Penalty).
```bash
tax-commander pay --parcel P-001 --amount 441.00 --date 2025-04-15
```

**Option B: AI Check Ingestion 🤖**
Simply point the tool at an image of a check. It handles the typing for you.
```bash
tax-commander ingest check_image.jpg
```

**Option C: Installment Plans**
For residents paying in installments (if enabled).
```bash
tax-commander pay --parcel P-001 --amount 150.00 --date 2025-04-15 --installment-num 1
```

### 3. Generating Documents

**Issue Receipts**
Generate a formal "Certificate of Payment" PDF for a resident.
```bash
tax-commander receipt <TRANSACTION_ID>
```

**Bank Deposit Slips**
Generate a manifest for your bank run.
```bash
tax-commander deposit-slip 2025-04-20
```

**Reprinting Bills**
Lost bill? No problem.
```bash
tax-commander reprint-bill --parcel P-001
```

### 4. Handling Exceptions

**Bounced Checks (NSF)**
Record a reversal for a bounced check. This keeps the ledger accurate without deleting history.
```bash
tax-commander nsf <TRANSACTION_ID>
```

**Exonerations**
Process an official exoneration (tax forgiveness) for indigent residents or errors.
```bash
tax-commander exonerate --parcel P-099 --amount 50.00 --date 2025-05-01 --reason "Indigent"
```

### 5. Monthly Reporting
At the end of every month, generate your DCED report and close the books.

```bash
# 1. View the Dashboard
tax-commander dashboard

# 2. Generate Report & Remittance Advice
tax-commander report --month 04 --year 2025

# 3. Lock the Month
tax-commander close-month --month 04 --year 2025
```

### 6. End of Year
Generate the "Turnover Report" (Lien List) for the Tax Claim Bureau.
```bash
tax-commander turnover-report
```

---

## ⚙️ Configuration

Tax Commander is **municipality-agnostic**. Open `~/.config/tax-commander/config.yaml` to set:
*   **Municipality Name & Address**
*   **Millage Rates** (Township, County, School)
*   **Bank Account Details**
*   **Gemini API Key** (for AI features)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up the dev environment and run the test suite.

## 📜 License
MIT © [Charles E. Forsyth III](LICENSE)