# Table Reader (Bank Statement)

**Scope:** Extracts transactions from credit card statement PDFs (Santander-focused). Uses OCR (Tesseract), classifies MSI vs No a meses and Titular vs Adicional, exports CSV/Excel and a per-person Resumen. Table extraction runs in parallel (one thread per logical table; tables spanning pages are processed in the same thread).

**Python:** 3.14+

---

## Requirements

- **Python 3.14+**
- **Tesseract OCR** on your `PATH` (e.g. `brew install tesseract tesseract-lang` on macOS; `apt install tesseract-ocr tesseract-ocr-spa` on Ubuntu)
- Dependencies: see `requirements.txt` or `pyproject.toml` (pdfplumber, pytesseract, pandas, openpyxl, Pillow, numpy, python-dotenv)

---

## How to run

```bash
# 1. Clone and enter project
git clone <repo-url>
cd table-reader-bank

# 2. Create venv and install
python3.14 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Config (optional)
cp .env.example .env
# Edit .env with person names, mortgage total, splits, TABLE_NAME, etc.

# 4. Run
python main.py "path/to/estado_de_cuenta.pdf"
python main.py "path/to/estado_de_cuenta.pdf" --output-dir ./output
python main.py "path/to/estado_de_cuenta.pdf" --csv-only
python main.py "path/to/estado_de_cuenta.pdf" --excel-only
```

---

## Project structure

```
table-reader-bank/
├── main.py                 # CLI entry point
├── pyproject.toml         # Project metadata, Python ≥3.14, ruff/mypy
├── requirements.txt
├── .env.example
├── table_reader/           # Main package
│   ├── config.py          # .env loader (PEOPLE, SPLITS, MORTGAGE_TOTAL, etc.)
│   ├── constants.py       # RENDER_DPI, column names, AMOUNT_CHAR_WHITELIST
│   ├── extraction.py     # PDF → tables, parallel by logical table
│   ├── ocr.py            # Tesseract wrappers, sign detection
│   ├── data_cleaning.py   # Classification, date/amount cleaning, reconciliation
│   ├── summary.py        # Per-person Resumen with SUMIFS formulas
│   ├── export.py         # CSV (UTF-8 BOM) and Excel
│   └── lib/               # Shared pure helpers
│       ├── text.py        # sanitize_ocr, MONTHS_PATTERN, first_number, looks_numeric
│       └── image.py       # crop_cell_image, prepare_for_ocr, SCALE
└── output/                # Generated CSVs and Excel (gitignored)
```

---

## Configuration (.env)

Copy `.env.example` to `.env`. Main variables:

| Variable | Description |
|----------|-------------|
| `PEOPLE` | Comma-separated names (e.g. `Person1,Person2`) |
| `SHARED_LABEL` | Label for shared charges (default `Los 2`) |
| `MORTGAGE_TOTAL` | Monthly mortgage amount |
| `SPLITS` | Cost-split % matching PEOPLE order (e.g. `50,50`) |
| `TABLE_NAME` | Google Sheets table name for SUMIFS formulas |
| `EXPECTED_NOAMESES_CARGOS` / `EXPECTED_NOAMESES_ABONOS` | Optional; validate No a Meses totals |

---

## Output files

| File | Description |
|------|-------------|
| `msi_titular.csv` / `msi_adicional.csv` | MSI (installment) transactions |
| `no_a_meses_titular.csv` / `no_a_meses_adicional.csv` | Regular transactions by card |
| `no_a_meses_consolidado.csv` | All regular transactions merged |
| `resumen.csv` | Per-person summary (formulas for Debe, Los 2, Total Tarjeta, etc.) |
| `estado_de_cuenta.xlsx` | All sheets above in one workbook |

CSVs use **UTF-8 BOM** for correct import into Google Sheets (ñ, tildes). Fill the `De quien` column in the consolidated sheet; Resumen formulas update automatically.

---

## Summary table (Resumen)

Resumen contains **spreadsheet formulas** (`=SUMIFS(...)`, `=SUM(...)`). Open in Excel or Google Sheets; as you set `De quien` on the consolidated sheet, totals update. Columns: Nombre, Debe, Los 2, Total Tarjeta, Total hipoteca, Total de totales.

---

## How it works

1. PDF pages rendered at 300 DPI; pdfplumber finds table bounding boxes.
2. Tables are grouped (continuation tables attached to the previous logical table).
3. Each logical table is extracted in parallel (OCR cell-by-cell, Tesseract).
4. data_cleaning classifies rows, cleans dates/amounts, reconciles totals.
5. DataFrames built per sheet; No a Meses Titular + Adicional merged into Consolidado.
6. Export CSV (UTF-8 BOM) and/or Excel; Resumen built from config and formulas.

---

*Santander-focused; other banks may work but are not guaranteed.*
