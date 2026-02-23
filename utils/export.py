"""
Export utilities for CSV and Excel.

Google Sheets compatibility
---------------------------
* CSVs are saved with UTF-8-BOM (utf-8-sig) encoding so that Google Sheets
  correctly interprets special characters (tildes, ñ, etc.) when imported
  via File → Import or the Sheets API.
* Numbers in the "Monto" column are written as plain floats (no currency
  symbols) so Sheets automatically detects them as numeric.
* Dates are left as strings (DD-Mon-YYYY) because Sheets will auto-parse them.

To import a CSV into Google Sheets:
  1. Open Google Sheets → File → Import → Upload.
  2. Choose "Comma" as separator and "UTF-8" as encoding.
  3. Done — numbers, dates, and accented characters will display correctly.
"""

import os
import pandas as pd
from .summary import build_summary


def export_csv(dataframes: dict, output_dir: str) -> list:
    """Export each DataFrame to a Google-Sheets-compatible CSV (UTF-8 BOM)."""
    os.makedirs(output_dir, exist_ok=True)
    files = []
    for sheet_name, df in dataframes.items():
        filename = sheet_name.lower().replace(" ", "_") + ".csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        files.append(filepath)
        print(f"   💾 {filepath}")

    # Also export the summary table when a consolidated sheet exists
    if "No a Meses Consolidado" in dataframes:
        summary_df = build_summary()
        summary_path = os.path.join(output_dir, "resumen.csv")
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        files.append(summary_path)
        print(f"   💾 {summary_path}")

    return files


def export_excel(dataframes: dict, output_dir: str) -> str:
    """Export all DataFrames to an Excel workbook.

    Sheets:
      • One sheet per extracted category (MSI Titular, No a Meses Titular, …)
      • 'No a Meses Consolidado' sheet
      • 'Resumen' sheet — the per-person summary table

    Column widths are auto-fitted.  No heavy styling is applied so that the
    file can be opened in Google Sheets without layout issues.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "estado_de_cuenta.xlsx")

    # Build summary if possible
    summary_df = None
    if "No a Meses Consolidado" in dataframes:
        summary_df = build_summary()

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        # ── Transaction sheets ─────────────────────────────────────
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            _autofit_columns(writer.sheets[sheet_name], df)

        # ── Summary sheet ──────────────────────────────────────────
        if summary_df is not None:
            summary_df.to_excel(writer, sheet_name="Resumen", index=False)
            _autofit_columns(writer.sheets["Resumen"], summary_df)

            # Print summary to console
            print("\n📊 Resumen de gastos (Fórmulas generadas para la hoja de cálculo):")
            for _, row in summary_df.iterrows():
                print(f"   {row['Nombre']:<12} -> Fórmulas dinámicas (Excel/Sheets)")

    print(f"\n   💾 {filepath}")
    return filepath


# ── Helpers ────────────────────────────────────────────────────────────────────

def _autofit_columns(ws, df: pd.DataFrame, max_width: int = 50) -> None:
    """Set each column's width to the max content length (capped at max_width)."""
    for col_idx, col_name in enumerate(df.columns, 1):
        max_len = len(str(col_name))
        for val in df[col_name]:
            max_len = max(max_len, len(str(val)) if val is not None else 0)
        letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[letter].width = min(max_len + 2, max_width)
