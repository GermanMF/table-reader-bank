#!/usr/bin/env python3
"""
Bank Statement — Table Extractor
==================================================
Extracts transaction tables from a bank statement PDF (image-based)
and exports them to CSV and Excel, separated by category:
  - "Meses sin intereses" (MSI) — installment purchases
  - "No a meses" — regular charges/credits

Usage:
    python3 main.py "Estado de cuenta febrero 2026 - crop.pdf"
    python3 main.py "Estado de cuenta febrero 2026 - crop.pdf" --output-dir ./output
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from table_reader import process_pdf, export_csv, export_excel
from table_reader.config import EXPECTED_NOAMESES_CARGOS, EXPECTED_NOAMESES_ABONOS


def _validate_no_a_meses(dataframes: dict[str, pd.DataFrame]) -> None:
    """Print No a Meses totals and optionally compare to expected (.env)."""
    if "No a Meses Consolidado" not in dataframes:
        return
    df = dataframes["No a Meses Consolidado"]
    if df.empty or "Monto" not in df.columns or "Tipo" not in df.columns:
        return
    df = df.copy()
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
    cargos = df.loc[df["Tipo"] == "Cargo", "Monto"].sum()
    abonos = df.loc[df["Tipo"] == "Abono", "Monto"].sum()
    print("\n" + "=" * 60)
    print("  No a Meses — Totals")
    print("=" * 60)
    print(f"   Cargos: {cargos:,.2f}  |  Abonos: {abonos:,.2f}")
    if EXPECTED_NOAMESES_CARGOS is not None or EXPECTED_NOAMESES_ABONOS is not None:
        ok = True
        if EXPECTED_NOAMESES_CARGOS is not None:
            diff_c = abs(cargos - EXPECTED_NOAMESES_CARGOS)
            if diff_c < 0.01:
                print(f"   Cargos: ✅ matches expected {EXPECTED_NOAMESES_CARGOS:,.2f}")
            else:
                print(f"   Cargos: ⚠️  expected {EXPECTED_NOAMESES_CARGOS:,.2f} (diff {cargos - EXPECTED_NOAMESES_CARGOS:+,.2f})")
                ok = False
        if EXPECTED_NOAMESES_ABONOS is not None:
            diff_a = abs(abonos - EXPECTED_NOAMESES_ABONOS)
            if diff_a < 0.01:
                print(f"   Abonos: ✅ matches expected {EXPECTED_NOAMESES_ABONOS:,.2f}")
            else:
                print(f"   Abonos: ⚠️  expected {EXPECTED_NOAMESES_ABONOS:,.2f} (diff {abonos - EXPECTED_NOAMESES_ABONOS:+,.2f})")
                ok = False
        if not ok:
            print("   Tip: check PDF or OCR if totals don't match expected.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract transactions from a credit card PDF statement"
    )
    parser.add_argument("pdf_path", help="Path to the cropped PDF statement")
    parser.add_argument("--output-dir", "-o", default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--csv-only", action="store_true",
                        help="Export only CSV (skip Excel)")
    parser.add_argument("--excel-only", action="store_true",
                        help="Export only Excel (skip CSV)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    output_dir = Path(args.output_dir)

    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    print("=" * 60)
    print("  Bank Statement — Table Extractor")
    print("=" * 60)

    dataframes = process_pdf(pdf_path, output_dir)

    if not dataframes:
        print("\n❌ No tables extracted. Check the PDF file.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Exporting...")
    print("=" * 60)

    if not args.excel_only:
        export_csv(dataframes, output_dir)
    if not args.csv_only:
        export_excel(dataframes, output_dir)

    _validate_no_a_meses(dataframes)
    print(f"\n✅ Done! Files saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
