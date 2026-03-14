"""
Summary table builder (per-person breakdown with spreadsheet formulas).
"""

import pandas as pd

from table_reader.config import (
    PEOPLE,
    SHARED_LABEL,
    MORTGAGE_TOTAL,
    SPLIT,
    TABLE_NAME,
)

SUMMARY_COLUMNS = [
    "Nombre", "Debe", "Los 2",
    "Total Tarjeta", "Total hipoteca", "Total de totales",
]


def build_summary() -> pd.DataFrame:
    """Build the per-person summary table filled with spreadsheet formulas."""
    rows: list[dict[str, str | float]] = []

    for i, person in enumerate(PEOPLE):
        excel_row = i + 2
        split_frac = SPLIT[person]
        debe_formula = (
            f'=SUMIFS({TABLE_NAME}[Monto], {TABLE_NAME}[De quien], "{person}", '
            f'{TABLE_NAME}[Tipo], "Cargo")'
        )
        los_2_formula = (
            f'=SUMIFS({TABLE_NAME}[Monto], {TABLE_NAME}[De quien], "{SHARED_LABEL}", '
            f'{TABLE_NAME}[Tipo], "Cargo")*{split_frac:.4f}'
        )
        total_tarjeta = f"=B{excel_row}+C{excel_row}"
        total_hipoteca = round(MORTGAGE_TOTAL * split_frac, 2)
        total_totales = f"=D{excel_row}+E{excel_row}"
        rows.append({
            "Nombre": person,
            "Debe": debe_formula,
            "Los 2": los_2_formula,
            "Total Tarjeta": total_tarjeta,
            "Total hipoteca": total_hipoteca,
            "Total de totales": total_totales,
        })

    totals_row = len(PEOPLE) + 2
    shared_formula = (
        f'=SUMIFS({TABLE_NAME}[Monto], {TABLE_NAME}[De quien], "{SHARED_LABEL}", '
        f'{TABLE_NAME}[Tipo], "Cargo")'
    )
    sum_tarjeta = f"=SUM(D2:D{totals_row - 1})"
    sum_hipoteca = round(sum(SPLIT[p] * MORTGAGE_TOTAL for p in PEOPLE), 2)
    sum_totales = f"=SUM(F2:F{totals_row - 1})"
    rows.append({
        "Nombre": SHARED_LABEL,
        "Debe": shared_formula,
        "Los 2": shared_formula,
        "Total Tarjeta": sum_tarjeta,
        "Total hipoteca": sum_hipoteca,
        "Total de totales": sum_totales,
    })

    summary_df = pd.DataFrame(rows)
    return summary_df[SUMMARY_COLUMNS]
