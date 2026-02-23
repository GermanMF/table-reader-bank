#!/usr/bin/env python3
"""
Santander Credit Card Statement — Table Extractor
==================================================
Extracts transaction tables from a Santander bank statement PDF (image-based)
and exports them to CSV and Excel, separated by category:
  - "Meses sin intereses" (MSI) — installment purchases
  - "No a meses" — regular charges/credits

Usage:
    python3 main.py "Estado de cuenta febrero 2026 - crop.pdf"
    python3 main.py "Estado de cuenta febrero 2026 - crop.pdf" --output-dir ./output
"""

import argparse
import os
import sys

from utils.extraction import process_pdf
from utils.export import export_csv, export_excel

def main():
    parser = argparse.ArgumentParser(
        description="Extract transactions from Santander credit card PDF statement"
    )
    parser.add_argument("pdf_path", help="Path to the cropped PDF statement")
    parser.add_argument("--output-dir", "-o", default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--csv-only", action="store_true",
                        help="Export only CSV (skip Excel)")
    parser.add_argument("--excel-only", action="store_true",
                        help="Export only Excel (skip CSV)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"❌ File not found: {args.pdf_path}")
        sys.exit(1)

    print("=" * 60)
    print("  Santander Statement — Table Extractor")
    print("=" * 60)

    dataframes = process_pdf(args.pdf_path, args.output_dir)

    if not dataframes:
        print("\n❌ No tables extracted. Check the PDF file.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Exporting...")
    print("=" * 60)

    if not args.excel_only:
        export_csv(dataframes, args.output_dir)
    if not args.csv_only:
        export_excel(dataframes, args.output_dir)

    print(f"\n✅ Done! Files saved to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
