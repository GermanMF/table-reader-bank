"""
Summary table builder.

Produces a per-person breakdown identical to the table shown in the
side panel of the spreadsheet:

  Nombre | Debe | Los 2 | Total Tarjeta | Total hipoteca | Total de totales

The generator outputs actual spreadsheet formulas (e.g. =SUMIFS(...)) 
so the amounts calc automatically in Excel/Google Sheets as the user 
manually assigns the 'De quien' column later.
"""

import pandas as pd
from .config import (
    PEOPLE, SHARED_LABEL,
    MORTGAGE_TOTAL, SPLIT, TABLE_NAME
)


def build_summary() -> pd.DataFrame:
    """
    Build the per-person summary table filled with spreadsheet formulas.
    """
    rows = []
    sheet = "'No a Meses Consolidado'"
    
    # We will output rows where Nombre is the first column (A)
    # Debe -> Column B
    # Los 2 -> Column C
    # Total Tarjeta -> Column D
    # Total hipoteca -> Column E
    # Total de totales -> Column F
    # The named table references uses columns: [Monto], [Tipo], [De quien]
    
    # Data rows start at Excel row 2 (row 1 is headers)
    for i, person in enumerate(PEOPLE):
        excel_row = i + 2
        split_frac = SPLIT[person]
        
        # Debe = explicit personal charge
        debe_formula = f'=SUMIFS({TABLE_NAME}[Monto], {TABLE_NAME}[De quien], "{person}", {TABLE_NAME}[Tipo], "Cargo")'
        
        # Los 2 = string formula of shared portion
        los_2_formula = f'=SUMIFS({TABLE_NAME}[Monto], {TABLE_NAME}[De quien], "{SHARED_LABEL}", {TABLE_NAME}[Tipo], "Cargo")*{split_frac:.4f}'
        
        # Totals
        total_tarjeta = f'=B{excel_row}+C{excel_row}'
        total_hipoteca = round(MORTGAGE_TOTAL * split_frac, 2)
        total_totales = f'=D{excel_row}+E{excel_row}'
        
        rows.append({
            "Nombre": person,
            "Debe": debe_formula,
            "Los 2": los_2_formula,
            "Total Tarjeta": total_tarjeta,
            "Total hipoteca": total_hipoteca,
            "Total de totales": total_totales,
        })
        
    # Totals row for the summary table
    totals_row = len(PEOPLE) + 2
    
    shared_formula = f'=SUMIFS({TABLE_NAME}[Monto], {TABLE_NAME}[De quien], "{SHARED_LABEL}", {TABLE_NAME}[Tipo], "Cargo")'
    sum_tarjeta = f'=SUM(D2:D{totals_row-1})'
    sum_hipoteca = round(sum(SPLIT[p] * MORTGAGE_TOTAL for p in PEOPLE), 2)
    sum_totales = f'=SUM(F2:F{totals_row-1})'

    rows.append({
        "Nombre": SHARED_LABEL,
        "Debe": shared_formula,
        "Los 2": shared_formula,
        "Total Tarjeta": sum_tarjeta,
        "Total hipoteca": sum_hipoteca,
        "Total de totales": sum_totales,
    })

    summary_df = pd.DataFrame(rows)
    # Reorder fully just in case
    summary_df = summary_df[[
        "Nombre", "Debe", "Los 2", 
        "Total Tarjeta", "Total hipoteca", "Total de totales"
    ]]
    return summary_df
