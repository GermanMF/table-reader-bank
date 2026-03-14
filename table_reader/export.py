"""
Export utilities for CSV and Excel (Google Sheets compatible).
"""

from pathlib import Path

import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from table_reader.summary import build_summary


def export_csv(
    dataframes: dict[str, pd.DataFrame], output_dir: Path | str
) -> list[Path]:
    """Export each DataFrame to a Google-Sheets-compatible CSV (UTF-8 BOM)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for sheet_name, df in dataframes.items():
        filename = sheet_name.lower().replace(" ", "_") + ".csv"
        filepath = out / filename
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        files.append(filepath)
        print(f"   💾 {filepath}")

    if "No a Meses Consolidado" in dataframes:
        summary_df = build_summary()
        summary_path = out / "resumen.csv"
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        files.append(summary_path)
        print(f"   💾 {summary_path}")

    return files


def export_excel(
    dataframes: dict[str, pd.DataFrame], output_dir: Path | str
) -> Path:
    """
    Export all DataFrames to an Excel workbook.
    One sheet per category plus 'Resumen'. Column widths auto-fitted.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    filepath = out / "estado_de_cuenta.xlsx"

    summary_df: pd.DataFrame | None = None
    if "No a Meses Consolidado" in dataframes:
        summary_df = build_summary()

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            _autofit_columns(writer.sheets[sheet_name], df)
        if summary_df is not None:
            summary_df.to_excel(writer, sheet_name="Resumen", index=False)
            _autofit_columns(writer.sheets["Resumen"], summary_df)
            print("\n📊 Resumen de gastos (Fórmulas generadas para la hoja de cálculo):")
            for _, row in summary_df.iterrows():
                print(f"   {row['Nombre']:<12} -> Fórmulas dinámicas (Excel/Sheets)")

    print(f"\n   💾 {filepath}")
    return filepath


def _autofit_columns(ws: Worksheet, df: pd.DataFrame, max_width: int = 50) -> None:
    """Set each column width to max content length (capped at max_width)."""
    for col_idx, col_name in enumerate(df.columns, 1):
        max_len = len(str(col_name))
        for val in df[col_name]:
            max_len = max(max_len, len(str(val)) if val is not None else 0)
        letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[letter].width = min(max_len + 2, max_width)
