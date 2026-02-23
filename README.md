# TableReaderProj 🏦

> **Santander Credit Card Statement — Automated Table Extractor**
>
> Extracts transaction tables from image-based Santander PDF bank statements using OCR, cleans and classifies the data, and exports it to CSV (Google Sheets–ready) and Excel — including a per-person shared-expense summary table.

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Configuration (.env)](#configuration-env)
6. [Usage](#usage)
7. [Output Files](#output-files)
8. [Google Sheets Integration](#google-sheets-integration)
9. [Summary Table Logic](#summary-table-logic)
10. [How It Works](#how-it-works)

---

## Features

- 📄 **PDF → OCR** — Renders each page at 300 DPI and uses Tesseract OCR to read individual table cells.
- 🔠 **Smart date & amount cleaning** — Fixes common OCR mis-reads (`f→7`, `O→0`, border bleed, extra digits).
- 🗂 **Automatic classification** — Separates *Meses sin intereses* (MSI) from *No a meses* (regular) and *Titular* from *Adicional* cards.
- 📊 **Consolidated sheet** — Merges Titular + Adicional regular transactions into one view.
- 👥 **Per-person summary table** — Produces a Resumen sheet/CSV showing each person's liability, shared amounts, and mortgage contribution.
- ⚙️ **Configurable via `.env`** — Person names, mortgage total, and cost-split percentages are all environment variables.
- 🌐 **Google Sheets–compatible** — CSVs are exported as UTF-8 BOM so special characters (ñ, tildes) import correctly.

---

## Project Structure

```
TableReaderProj/
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── .env                     # Your private config (gitignored)
├── .env.example             # Config template (committed)
├── .gitignore
├── utils/
│   ├── config.py            # Loads .env variables (person names, split, mortgage)
│   ├── extraction.py        # PDF rendering + cell-by-cell OCR extraction
│   ├── ocr.py               # Tesseract OCR helpers (crop, sharpen, sign detection)
│   ├── data_cleaning.py     # Date/amount/percentage cleaning + row classification
│   ├── summary.py           # Per-person expense summary table builder
│   └── export.py            # CSV & Excel export (Google Sheets compatible)
└── output/                  # Generated files (gitignored)
    ├── msi_titular.csv
    ├── msi_adicional.csv
    ├── no_a_meses_titular.csv
    ├── no_a_meses_adicional.csv
    ├── no_a_meses_consolidado.csv
    ├── resumen.csv           ← per-person summary
    └── estado_de_cuenta.xlsx ← all sheets + Resumen
```

---

## Requirements

| Dependency | Version | Purpose |
|---|---|---|
| `pdfplumber` | ≥ 0.10 | Table boundary detection in PDFs |
| `pytesseract` | ≥ 0.3.10 | Python wrapper for Tesseract OCR |
| `Pillow` | ≥ 10.0 | Image manipulation & cell cropping |
| `numpy` | ≥ 1.24 | Pixel-level sign detection (+/-) |
| `pandas` | ≥ 2.0 | DataFrame manipulation & export |
| `openpyxl` | ≥ 3.1 | Excel (.xlsx) file writing |
| `python-dotenv` | ≥ 1.0 | Loads `.env` configuration file |

> **System requirement:** [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) must be installed and available on your `PATH`.
> - macOS: `brew install tesseract tesseract-lang`
> - Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-spa`

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd TableReaderProj

# 2. Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy config template and fill in your values
cp .env.example .env
# Edit .env with your preferred names, mortgage total, and split percentages
```

---

## Configuration (.env)

All shared-expense settings live in a `.env` file at the project root.  
Copy `.env.example` to `.env` and customise:

```env
# Comma-separated list of people who share the credit card expenses.
# You can add as many as you want (e.g. PERSON1,PERSON2,PERSON3)
PEOPLE=Liz,Germán

# The "De quien" column label used for shared expenses
SHARED_LABEL=Los 2

# Total monthly mortgage amount (same currency as transactions)
MORTGAGE_TOTAL=26000

# Cost-split percentages (comma-separated, matches order of PEOPLE)
# Must add up to 100
SPLITS=50,50
```

**Common split examples:**

| Scenario | `SPLITS` |
|---|---|
| Even (default) | `50,50` |
| 60/40 | `60,40` |
| 40/60 | `40,60` |
| 3 people | `33.3,33.3,33.4` |

---

## Usage

```bash
# Basic usage (outputs to ./output by default)
python3 main.py "Estado de cuenta febrero 2026 - crop.pdf"

# Specify a custom output directory
python3 main.py "Estado de cuenta.pdf" --output-dir ./my_output

# Export CSV only (skip Excel)
python3 main.py "Estado de cuenta.pdf" --csv-only

# Export Excel only (skip CSV)
python3 main.py "Estado de cuenta.pdf" --excel-only
```

---

## Output Files

| File | Description |
|---|---|
| `msi_titular.csv / _adicional.csv` | Installment (MSI) transactions |
| `no_a_meses_titular.csv / _adicional.csv` | Regular transactions by card |
| `no_a_meses_consolidado.csv` | All regular transactions merged |
| `resumen.csv` | Per-person summary table |
| `estado_de_cuenta.xlsx` | All sheets above in one workbook |

### Transaction columns (No a meses)

| Column | Description |
|---|---|
| `Fecha Transacción` | Date the transaction occurred |
| `Fecha Cargo` | Date the charge was posted |
| `Descripción` | Merchant / description |
| `Monto` | Amount (positive number) |
| `Tipo` | `Cargo` (charge) or `Abono` (credit) |
| `Tipo Tarjeta` | `Titular` or `Adicional` |
| `De quien` | **Manually filled:** `Liz`, `Germán`, or `Los 2` |
| `Comentario` | Optional free-text note |

> ℹ️ The `De quien` and `Comentario` columns are left blank by the extractor. Fill them in Google Sheets or Excel, then the summary will auto-update on the next run.

---

## Google Sheets Integration

The CSV files are saved with **UTF-8 BOM** (`utf-8-sig`) encoding, which ensures Google Sheets correctly renders Spanish characters (ñ, á, é, etc.) without any manual encoding selection.

### Import steps

1. Open [Google Sheets](https://sheets.google.com) → **File → Import**
2. Click **Upload** and select any `.csv` from the `output/` folder
3. Set **Separator**: Comma, **Encoding**: UTF-8, **Convert text to numbers/dates**: Yes
4. Click **Import data**

### Column type hints for Sheets

After importing, select the following columns and format them for better usability:

| Column | Format |
|---|---|
| `Fecha Transacción`, `Fecha Cargo` | Date (Sheets usually auto-detects) |
| `Monto`, `Debe`, `Total*` | Number → Currency |
| `Tipo` | Use Data Validation → dropdown: `Cargo`, `Abono` |
| `De quien` | Use Data Validation → dropdown: `Liz`, `Germán`, `Los 2` |

---

## Summary Table Logic

The **Resumen** (`resumen.csv` / `Resumen` Excel sheet) is generated as a template full of **live spreadsheet formulas** (`=SUMIFS(...)`, `SUM()`).

When you export and open the files in Google Sheets or Excel, the Resumen table will automatically calculate the totals as you manually fill in the `De quien` column on the **No a Meses Consolidado** sheet.

### Columns

| Column | Description |
|---|---|
| `Nombre` | Person name + a totals row |
| `Debe` | `=SUMIFS` referencing their direct individual charges |
| `Los 2` | `=SUMIFS` referencing the shared charges, multiplied by their `%` share |
| `Total Tarjeta` | `= Debe + Los 2` |
| `Total hipoteca` | `MORTGAGE_TOTAL × split_fraction` (outputted as a hardcoded static value per your request) |
| `Total de totales` | `= Total Tarjeta + Total hipoteca` |

### Dynamic configuration
You can add from 1 to N number of people. The summary builder will automatically construct formulas matching your configured `PEOPLE` list and distribute the total `MORTGAGE_TOTAL` using the `SPLITS` percentages!

---

## How It Works

```
PDF (image-based)
  │
  ▼ pdfplumber → finds table bounding boxes
  │
  ▼ Pillow → renders pages at 300 DPI
  │
  ▼ Tesseract OCR → reads each cell (PSM 7 / PSM 6)
  │
  ▼ data_cleaning.py → fixes dates, amounts, classifies rows
  │
  ▼ extraction.py → assembles DataFrames per category/card
  │
  ├──▶ msi_titular / msi_adicional
  ├──▶ no_a_meses_titular / no_a_meses_adicional
  ├──▶ no_a_meses_consolidado
  │
  ▼ summary.py → per-person totals table (reads .env config)
  │
  ▼ export.py → CSV (UTF-8 BOM) + Excel (.xlsx)
```

---

*Generated by [table-reader-bank](https://github.com/GermanMF/table-reader-bank) — last updated February 2026.*
