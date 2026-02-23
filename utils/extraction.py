"""
Main table extraction logic.
"""

import pdfplumber
import pandas as pd
from PIL import Image
from .ocr import ocr_cell, detect_sign_cell, ocr_region
from .data_cleaning import (
    classify_table, is_header_row, is_total_row,
    clean_msi_dataframe, clean_regular_dataframe
)

MSI_COLUMNS = [
    "Fecha de la operación",
    "Descripción",
    "Monto original",
    "Saldo pendiente",
    "Pago requerido",
    "Núm. de pago",
    "Tasa de interés aplicable",
]

REGULAR_RAW_COLUMNS = [
    "Fecha de la operación",
    "Fecha de cargo",
    "Descripción del movimiento",
    "Tipo",
    "Monto",
]

RENDER_DPI = 300

def extract_table_data(page_img: Image.Image, table, page_index: int) -> tuple:
    """
    Extract data from a pdfplumber Table using cell-by-cell OCR.
    Returns (category, card_type, data_rows).
    """
    rows = table.rows
    if not rows:
        return None, None, []

    # --- Detect header/title rows (merged cells = section title) ---
    header_text = ""
    data_start_idx = 0

    for ri, row in enumerate(rows):
        cells = row.cells
        non_none = [c for c in cells if c is not None]

        if len(non_none) <= 1:
            # Merged header row — OCR it for classification only
            if non_none:
                text = ocr_region(page_img, non_none[0])
                header_text += " " + text
            data_start_idx = ri + 1
        else:
            break

    category, card_type = classify_table(header_text)
    if category == "unknown":
        return "continuation", None, []

    # --- Determine if this is MSI (7 cols) or Regular (5 cols) ---
    is_msi = (category == "msi")
    expected_cols = 7 if is_msi else 5

    # --- Extract data rows (skip column header rows) ---
    data_rows = []
    for ri in range(data_start_idx, len(rows)):
        row = rows[ri]
        cells = row.cells
        non_none_cells = [(ci, c) for ci, c in enumerate(cells) if c is not None]

        # Skip rows with too few cells (likely merged/header)
        if len(non_none_cells) < 3:
            continue

        row_data = []
        for ci, cell in enumerate(cells):
            if cell is None:
                row_data.append("")
                continue

            cell_width = cell[2] - cell[0]

            # Special handling for the narrow +/- column in Regular tables
            if not is_msi and cell_width < 20:
                text = detect_sign_cell(page_img, cell)
            else:
                text = ocr_cell(page_img, cell)

            row_data.append(text)

        # Skip header rows and total/summary rows
        if is_header_row(row_data) or is_total_row(row_data):
            continue

        # Skip empty rows
        if not any(row_data):
            continue

        # Normalize to expected column count
        while len(row_data) < expected_cols:
            row_data.append("")
        row_data = row_data[:expected_cols]

        data_rows.append(row_data)

    return category, card_type, data_rows


def extract_continuation_table(page_img: Image.Image, table) -> list:
    """
    Extract rows from a continuation table (no header).
    Used for Page 2 Table 1 which continues Page 1's Regular Titular table.
    """
    rows = table.rows
    data_rows = []

    for row in rows:
        cells = row.cells
        non_none_cells = [(ci, c) for ci, c in enumerate(cells) if c is not None]
        if len(non_none_cells) < 3:
            continue

        row_data = []
        for ci, cell in enumerate(cells):
            if cell is None:
                row_data.append("")
                continue
            cell_width = cell[2] - cell[0]
            if cell_width < 20:
                text = detect_sign_cell(page_img, cell)
            else:
                text = ocr_cell(page_img, cell)
            row_data.append(text)

        if is_header_row(row_data) or is_total_row(row_data):
            continue
        if not any(row_data):
            continue

        while len(row_data) < 5:
            row_data.append("")
        row_data = row_data[:5]
        data_rows.append(row_data)

    return data_rows


def process_pdf(pdf_path: str, output_dir: str) -> dict:
    """Process the PDF and return extracted DataFrames."""
    pdf = pdfplumber.open(pdf_path)

    print(f"📄 Opening PDF: {pdf_path}")
    print(f"   Pages: {len(pdf.pages)}")

    # Render pages
    page_images = []
    for i, page in enumerate(pdf.pages):
        img = page.to_image(resolution=RENDER_DPI)
        pil_img = img.original
        page_images.append(pil_img)
        print(f"   ✅ Page {i+1} rendered ({pil_img.width}×{pil_img.height}px)")

    # Storage
    tables_data = {
        "MSI Titular": [],
        "MSI Adicional": [],
        "No a Meses Titular": [],
        "No a Meses Adicional": [],
    }

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    }

    last_category = None
    last_card_type = "titular"

    for pi, page in enumerate(pdf.pages):
        page_img = page_images[pi]
        found_tables = page.find_tables(table_settings)

        print(f"\n🔍 Page {pi+1}: {len(found_tables)} table(s)")

        for ti, table in enumerate(found_tables):
            rows_count = len(table.rows)
            print(f"   📊 Table {ti+1} ({rows_count} rows)...", end=" ", flush=True)

            # Try to classify and extract
            category, card_type, data_rows = extract_table_data(
                page_img, table, pi
            )

            if category == "continuation":
                # Continuation of previous table (no header)
                data_rows = extract_continuation_table(page_img, table)
                if data_rows and last_category:
                    category = last_category
                    card_type = last_card_type
                else:
                    print(f"⏭️  Skipped (continuation, no context)")
                    continue

            if not data_rows:
                print(f"⏭️  Skipped (no data)")
                continue

            # Determine sheet name
            if category == "msi":
                sheet = f"MSI {'Adicional' if card_type == 'adicional' else 'Titular'}"
            elif category == "regular":
                sheet = f"No a Meses {'Adicional' if card_type == 'adicional' else 'Titular'}"
            else:
                print(f"⏭️  Skipped (unknown)")
                continue

            tables_data[sheet].extend(data_rows)
            last_category = category
            last_card_type = card_type

            print(f"✅ {category}/{card_type} — {len(data_rows)} rows → [{sheet}]")

    # Build DataFrames
    result = {}
    for sheet_name, rows in tables_data.items():
        if not rows:
            print(f"\n📋 {sheet_name}: (empty)")
            continue
        
        is_msi = "MSI" in sheet_name
        cols = MSI_COLUMNS if is_msi else REGULAR_RAW_COLUMNS
        df = pd.DataFrame(rows, columns=cols)
        
        if is_msi:
            df = clean_msi_dataframe(df)
        else:
            card_type = "adicional" if "Adicional" in sheet_name else "titular"
            df = clean_regular_dataframe(df, card_type)
            
        result[sheet_name] = df
        print(f"\n📋 {sheet_name}: {len(df)} transactions")

    # --- Build Consolidated No a Meses ---
    no_meses_dfs = []
    if "No a Meses Titular" in result and not result["No a Meses Titular"].empty:
        no_meses_dfs.append(result["No a Meses Titular"])
    if "No a Meses Adicional" in result and not result["No a Meses Adicional"].empty:
        no_meses_dfs.append(result["No a Meses Adicional"])
        
    if no_meses_dfs:
        consolidated_df = pd.concat(no_meses_dfs, ignore_index=True)
        result["No a Meses Consolidado"] = consolidated_df
        print(f"\n📋 No a Meses Consolidado: {len(consolidated_df)} transactions")

    return result
