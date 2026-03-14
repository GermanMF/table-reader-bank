"""
Main table extraction logic.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pdfplumber
import pandas as pd
from PIL import Image

from table_reader.config import EXPECTED_NOAMESES_CARGOS, EXPECTED_NOAMESES_ABONOS
from table_reader.constants import (
    RENDER_DPI,
    MSI_COLUMNS,
    REGULAR_RAW_COLUMNS,
)
from table_reader.ocr import ocr_cell, detect_sign_cell, ocr_region, AMOUNT_CHAR_WHITELIST
from table_reader.data_cleaning import (
    classify_table,
    is_header_row,
    is_total_row,
    parse_total_row,
    clean_msi_dataframe,
    clean_regular_dataframe,
    clean_amount,
    reconcile_totals_and_fix,
)
from table_reader.lib.text import looks_numeric

# Max workers for table-level parallel extraction
_MAX_EXTRACT_WORKERS = 4


def _segment_classify(
    page_img: Image.Image, table
) -> tuple[str, str | None]:
    """
    Classify a table segment from header only (OCR merged cells).
    Returns (category, card_type) with category in ('msi','regular','continuation','unknown'),
    card_type in ('titular','adicional') or None for continuation.
    """
    rows = table.rows
    if not rows:
        return "unknown", None
    header_text = ""
    for ri, row in enumerate(rows):
        cells = row.cells
        non_none = [c for c in cells if c is not None]
        if len(non_none) <= 1:
            if non_none:
                text = ocr_region(page_img, non_none[0])
                header_text += " " + text
        else:
            break
    category, card_type = classify_table(header_text)
    if category == "unknown":
        return "continuation", None
    return category, card_type


def _build_table_groups(
    pages: list,
    page_images: list[Image.Image],
    table_settings: dict,
) -> list[list[tuple[int, int, object]]]:
    """
    Build groups of table segments. Each group is a list of (page_idx, table_idx, table).
    Tables that continue onto the next page are in the same group.
    """
    groups: list[list[tuple[int, int, object]]] = []
    current_group: list[tuple[int, int, object]] | None = None
    last_category: str | None = None
    last_card_type: str | None = None

    for pi, page in enumerate(pages):
        found_tables = page.find_tables(table_settings)
        for ti, table in enumerate(found_tables):
            category, card_type = _segment_classify(page_images[pi], table)
            if category == "continuation" and current_group is not None:
                current_group.append((pi, ti, table))
            else:
                current_group = [(pi, ti, table)]
                groups.append(current_group)
                if category not in ("continuation", "unknown"):
                    last_category = category
                    last_card_type = card_type or "titular"
    return groups


def _process_group(
    group: list[tuple[int, int, object]],
    page_images: list[Image.Image],
) -> tuple[int, int, str, list[list], dict[str, str]]:
    """
    Extract one logical table (possibly spanning pages). Returns
    (first_page_idx, first_table_idx, sheet_name, data_rows, totals).
    """
    first_pi, first_ti, first_table = group[0]
    page_img0 = page_images[first_pi]

    category, card_type, data_rows, totals = extract_table_data(
        page_img0, first_table, first_pi
    )

    for pi, ti, table in group[1:]:
        page_img = page_images[pi]
        cont_rows, cont_totals = extract_continuation_table(page_img, table)
        data_rows.extend(cont_rows)
        if cont_totals:
            totals.update(cont_totals)

    # First segment is never continuation (groups are built so continuations attach to previous)
    if category == "msi":
        sheet_name = f"MSI {'Adicional' if card_type == 'adicional' else 'Titular'}"
    elif category == "regular":
        sheet_name = f"No a Meses {'Adicional' if card_type == 'adicional' else 'Titular'}"
    else:
        sheet_name = ""  # unknown: skip in aggregation

    return (first_pi, first_ti, sheet_name, data_rows, totals)


def _ocr_regular_row(
    page_img: Image.Image, cells: list, row_data: list
) -> None:
    """Fill row_data in place for a regular (5-col) table row; cells may have Nones."""
    for ci, cell in enumerate(cells):
        if cell is None:
            row_data.append("")
            continue
        cell_width = cell[2] - cell[0]
        if cell_width < 20:
            text = detect_sign_cell(page_img, cell)
        elif ci == 4:
            text = ocr_cell(page_img, cell, char_whitelist=AMOUNT_CHAR_WHITELIST)
        else:
            text = ocr_cell(page_img, cell)
        row_data.append(text)


def extract_table_data(
    page_img: Image.Image, table, page_index: int
) -> tuple[str | None, str | None, list, dict[str, str]]:
    """
    Extract data from a pdfplumber Table using cell-by-cell OCR.
    Returns (category, card_type, data_rows, totals).
    """
    rows = table.rows
    if not rows:
        return None, None, [], {}

    header_text = ""
    data_start_idx = 0
    for ri, row in enumerate(rows):
        cells = row.cells
        non_none = [c for c in cells if c is not None]
        if len(non_none) <= 1:
            if non_none:
                text = ocr_region(page_img, non_none[0])
                header_text += " " + text
            data_start_idx = ri + 1
        else:
            break

    category, card_type = classify_table(header_text)
    if category == "unknown":
        return "continuation", None, [], {}

    is_msi = category == "msi"
    expected_cols = 7 if is_msi else 5
    data_rows: list[list] = []
    totals: dict[str, str] = {}

    for ri in range(data_start_idx, len(rows)):
        row = rows[ri]
        cells = row.cells
        non_none_cells = [(ci, c) for ci, c in enumerate(cells) if c is not None]
        if len(non_none_cells) < 3:
            continue

        row_data: list[str] = []
        if is_msi:
            for ci, cell in enumerate(cells):
                if cell is None:
                    row_data.append("")
                    continue
                text = ocr_cell(page_img, cell)
                row_data.append(text)
        else:
            _ocr_regular_row(page_img, cells, row_data)

        if is_total_row(row_data):
            parsed = parse_total_row(row_data)
            if parsed:
                kind, amount_str = parsed
                totals["total_" + kind] = amount_str
            continue
        if is_header_row(row_data):
            continue
        if not any(row_data):
            continue
        while len(row_data) < expected_cols:
            row_data.append("")
        row_data = row_data[:expected_cols]
        data_rows.append(row_data)

    return category, card_type, data_rows, totals


def extract_continuation_table(
    page_img: Image.Image, table
) -> tuple[list[list], dict[str, str]]:
    """
    Extract rows from a continuation table (no header).
    Returns (data_rows, totals).
    """
    rows = table.rows
    data_rows: list[list] = []
    totals: dict[str, str] = {}

    for row in rows:
        cells = row.cells
        non_none_cells = [(ci, c) for ci, c in enumerate(cells) if c is not None]
        if len(non_none_cells) < 2:
            continue

        row_data: list[str] = []
        _ocr_regular_row(page_img, cells, row_data)

        if is_total_row(row_data):
            parsed = parse_total_row(row_data)
            if parsed:
                kind, amount_str = parsed
                totals["total_" + kind] = amount_str
            continue
        if is_header_row(row_data):
            continue
        if not any(str(x).strip() for x in row_data):
            continue
        while len(row_data) < 5:
            row_data.append("")
        row_data = row_data[:5]

        non_empty = [(i, str(x).strip()) for i, x in enumerate(row_data) if x]
        if len(non_empty) == 2:
            a, b = non_empty[0][1], non_empty[1][1]
            a_clean = clean_amount(a)
            b_clean = clean_amount(b)
            a_is_num = looks_numeric(a_clean)
            b_is_num = looks_numeric(b_clean)
            if a_is_num and not b_is_num:
                row_data = ["", "", b, "+", a_clean or a]
            elif b_is_num and not a_is_num:
                row_data = ["", "", a, "+", b_clean or b]
        data_rows.append(row_data)

    return data_rows, totals


def _safe_float(value: str | None) -> float | None:
    """Parse string to float; return None if missing or invalid."""
    if value is None or not str(value).strip():
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def process_pdf(
    pdf_path: Path | str, output_dir: Path | str
) -> dict[str, pd.DataFrame]:
    """Process the PDF and return extracted DataFrames."""
    pdf = pdfplumber.open(pdf_path)
    pdf_path_str = str(pdf_path)

    print(f"📄 Opening PDF: {pdf_path_str}")
    print(f"   Pages: {len(pdf.pages)}")

    page_images: list[Image.Image] = []
    for i, page in enumerate(pdf.pages):
        img = page.to_image(resolution=RENDER_DPI)
        pil_img = img.original
        page_images.append(pil_img)
        print(f"   ✅ Page {i+1} rendered ({pil_img.width}×{pil_img.height}px)")

    tables_data: dict[str, list] = {
        "MSI Titular": [],
        "MSI Adicional": [],
        "No a Meses Titular": [],
        "No a Meses Adicional": [],
    }
    table_totals: dict[str, dict[str, str]] = {}
    table_settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

    groups = _build_table_groups(pdf.pages, page_images, table_settings)
    total_tables = sum(len(g) for g in groups)
    print(f"\n🔍 Tables found: {total_tables} segment(s) in {len(groups)} logical table(s)")

    group_results: list[tuple[int, int, str, list, dict[str, str]]] = []
    with ThreadPoolExecutor(max_workers=_MAX_EXTRACT_WORKERS) as executor:
        futures = {
            executor.submit(_process_group, group, page_images): group
            for group in groups
        }
        for future in as_completed(futures):
            group = futures[future]
            first_pi, first_ti, sheet_name, data_rows, totals = future.result()
            if not sheet_name or not data_rows:
                continue
            group_results.append((first_pi, first_ti, sheet_name, data_rows, totals))

    # Sort by document order and aggregate
    group_results.sort(key=lambda x: (x[0], x[1]))
    for _pi, _ti, sheet_name, data_rows, totals in group_results:
        tables_data[sheet_name].extend(data_rows)
        if totals:
            table_totals.setdefault(sheet_name, {}).update(totals)
        cat = "msi" if "MSI" in sheet_name else "regular"
        card = "adicional" if "Adicional" in sheet_name else "titular"
        print(f"   ✅ {cat}/{card} — {len(data_rows)} rows → [{sheet_name}]")

    result: dict[str, pd.DataFrame] = {}
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
            totals = table_totals.get(sheet_name, {})
            total_cargos = _safe_float(totals.get("total_cargos"))
            total_abonos = _safe_float(totals.get("total_abonos"))
            if total_cargos is not None or total_abonos is not None:
                corrections = reconcile_totals_and_fix(df, total_cargos, total_abonos)
                for idx, old_val, new_val in corrections:
                    print(f"   🔧 Corrected OCR amount row {idx}: {old_val} → {new_val} (reconciled with statement total)")
        result[sheet_name] = df
        print(f"\n📋 {sheet_name}: {len(df)} transactions")

    no_meses_dfs: list[pd.DataFrame] = []
    if "No a Meses Titular" in result and not result["No a Meses Titular"].empty:
        no_meses_dfs.append(result["No a Meses Titular"])
    if "No a Meses Adicional" in result and not result["No a Meses Adicional"].empty:
        no_meses_dfs.append(result["No a Meses Adicional"])

    if no_meses_dfs:
        consolidated_df = pd.concat(no_meses_dfs, ignore_index=True)
        if EXPECTED_NOAMESES_CARGOS is not None or EXPECTED_NOAMESES_ABONOS is not None:
            corrections = reconcile_totals_and_fix(
                consolidated_df,
                total_cargos=EXPECTED_NOAMESES_CARGOS,
                total_abonos=EXPECTED_NOAMESES_ABONOS,
            )
            n_titular = len(result.get("No a Meses Titular", pd.DataFrame()))
            for idx, old_val, new_val in corrections:
                print(f"   🔧 Corrected OCR amount row {idx}: {old_val} → {new_val} (reconciled with expected total)")
                if idx < n_titular and "No a Meses Titular" in result:
                    result["No a Meses Titular"].at[idx, "Monto"] = new_val
                elif "No a Meses Adicional" in result:
                    result["No a Meses Adicional"].at[idx - n_titular, "Monto"] = new_val
        result["No a Meses Consolidado"] = consolidated_df
        print(f"\n📋 No a Meses Consolidado: {len(consolidated_df)} transactions")

    return result
