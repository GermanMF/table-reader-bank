"""
Export utilities for CSV and Excel.
"""

import os
import pandas as pd

def export_csv(dataframes: dict, output_dir: str) -> list:
    """Export each DataFrame to CSV."""
    os.makedirs(output_dir, exist_ok=True)
    files = []
    for sheet_name, df in dataframes.items():
        filename = sheet_name.lower().replace(" ", "_") + ".csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        files.append(filepath)
        print(f"   💾 {filepath}")
    return files


def export_excel(dataframes: dict, output_dir: str) -> str:
    """Export all DataFrames to a raw Excel workbook (no styling)."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "estado_de_cuenta.xlsx")

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]

            # --- Basic Column widths ---
            for col_idx, col_name in enumerate(df.columns, 1):
                max_len = len(str(col_name))
                for val in df[col_name]:
                    max_len = max(max_len, len(str(val)) if val else 0)
                letter = ws.cell(row=1, column=col_idx).column_letter
                ws.column_dimensions[letter].width = min(max_len + 2, 50)

    print(f"   💾 {filepath}")
    return filepath
