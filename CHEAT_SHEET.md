# ⚡ Tax Commander Cheat Sheet

## 💵 Processing Payments
| Action | Command |
| :--- | :--- |
| **Pay Check** | `python3 tax_commander.py pay --parcel P-001 --amount 441.00 --date 2025-04-15 --check 101` |
| **Pay Cash** | `python3 tax_commander.py pay --parcel P-001 --amount 441.00 --date 2025-04-15` |
| **Installment** | `python3 tax_commander.py pay --parcel P-001 --amount 150.00 --date 2025-04-15 --installment-num 1` |
| **Update Info** | `python3 tax_commander.py update-parcel --parcel P-001 --address "New Address"` |

## 📄 Paperwork & Receipts
| Action | Command |
| :--- | :--- |
| **Receipt** | `python3 tax_commander.py receipt <TX_ID>` (PDF saved to `receipts/`) |
| **Deposit Slip**| `python3 tax_commander.py deposit-slip 2025-04-20` |
| **Reprint Bill**| `python3 tax_commander.py reprint-bill --parcel P-001` |
| **Mailing Labels**| `python3 tax_commander.py export-labels` |

## 📊 Reports & Meetings
| Action | Command |
| :--- | :--- |
| **Dashboard** | `python3 tax_commander.py dashboard` (Opens in Browser) |
| **Monthly Rpt** | `python3 tax_commander.py report --month 4 --year 2025` |
| **Turnover Rpt**| `python3 tax_commander.py turnover-report` (End of Year) |
| **Audit Log** | `python3 tax_commander.py audit` |

## 🛠️ Admin & Maintenance
| Action | Command |
| :--- | :--- |
| **Close Month** | `python3 tax_commander.py close-month --month 4 --year 2025` |
| **Exonerate** | `python3 tax_commander.py exonerate --parcel P-099 --amount 50.00 --date 2025-05-01 --reason "Indigent"` |
| **NSF Reversal**| `python3 tax_commander.py nsf <TX_ID>` |
| **Gen Bills** | `python3 tax_commander.py generate-bills` |

## 🖨️ Printing
| Action | Command |
| :--- | :--- |
| **List Printers** | `python3 tax_commander.py list-printers` |
| **Print Bills** | `python3 tax_commander.py print-bills --folder tax_bills/YYYY-MM_Type/ --printer "Printer_Name"` |
| **Print Labels** | `python3 tax_commander.py print-labels --printer "Printer_Name"` |