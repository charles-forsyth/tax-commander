# 🦅 Tax Commander

[![CI Status](https://github.com/charles-forsyth/tax-commander/actions/workflows/ci.yml/badge.svg)](https://github.com/charles-forsyth/tax-commander/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **The Open-Source Operating System for PA Tax Collectors**  
> Automate bills, enforce compliance, and ingest checks with AI—all from the terminal.

---

## 📸 Screenshots

*(Add a screenshot of the Web Dashboard here)*
*(Add a screenshot of a generated PDF Bill here)*

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
uv tool install git+ssh://git@github.com/charles-forsyth/tax-commander.git

# 2. Initialize Config
mkdir -p ~/.config/tax-commander
curl -o ~/.config/tax-commander/config.yaml https://raw.githubusercontent.com/charles-forsyth/tax-commander/master/config.yaml.example
```

---

## ⚡ Quick Start

**1. Initialize a New Year**
```bash
tax-commander init-db
tax-commander import-duplicate path/to/county_export.csv
```

**2. Process a Payment (AI Mode)**
```bash
# Point to a check image
tax-commander ingest check_image.jpg
```
*> System validates amount, date, and duplicate payment checks instantly.*

**3. Close the Month**
```bash
tax-commander report --month 04 --year 2025
tax-commander close-month --month 04 --year 2025
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
