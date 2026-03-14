"""
Data cleaning and table classification utilities.
"""

import re
import pandas as pd

from table_reader.lib.text import (
    sanitize_ocr,
    MONTHS_PATTERN,
    MONTH_MAP,
    first_number,
    looks_numeric,
)


def classify_table(header_text: str) -> tuple[str, str]:
    """
    Classify a table from its header.
    Returns (category, card_type): ('msi'|'regular'|'unknown', 'titular'|'adicional')
    """
    upper = header_text.upper()
    if "MESES SIN INTERESES" in upper or "DIFERIDOS" in upper:
        category = "msi"
    elif "NO A MESES" in upper or "REGULARES" in upper:
        category = "regular"
    else:
        category = "unknown"
    card_type = "adicional" if "ADICIONAL" in upper else "titular"
    return category, card_type


def clean_amount(raw: str) -> str:
    """Clean monetary amount: '$21,098.00' -> '21098.00'; also '599,90' -> '599.90'."""
    if not raw:
        return ""
    cleaned = raw.replace("$", "").replace(" ", "").replace("_", "").strip()
    if re.search(r",\d{2}(?:\D|$)", cleaned) and cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace("O", "0").replace("o", "0")
    cleaned = cleaned.replace("S", "5").replace("s", "5")
    cleaned = cleaned.replace("l", "1").replace("I", "1")
    cleaned = re.sub(r"(\d)/(\d)", r"\g<1>7\2", cleaned)
    return first_number(cleaned)


def clean_date(raw: str) -> str:
    """
    Clean date string and fix common OCR errors.
    Handles border bleed, day digit misreads, extra digit noise.
    """
    if not raw:
        return ""
    cleaned = sanitize_ocr(raw)
    months_inner = MONTHS_PATTERN[3:-1]  # strip (?: and )

    cleaned = re.sub(r"\b(\d)f(-" + MONTHS_PATTERN + r")", r"\g<1>7\2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(\d)/(-" + MONTHS_PATTERN + r")", r"\g<1>7\2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(\d{2})\d(-" + MONTHS_PATTERN + r")", r"\1\2", cleaned, flags=re.IGNORECASE)

    match = re.search(
        r"(\d{1,2})-(" + months_inner + r")-(\d{4})",
        cleaned, flags=re.IGNORECASE
    )
    if not match:
        match = re.search(r"(\d{1,2})-(" + months_inner + r")", cleaned, flags=re.IGNORECASE)
        if match:
            day = match.group(1)
            if len(day) == 1:
                day = "0" + day
            month_str = match.group(2).capitalize()
            month_num = MONTH_MAP.get(month_str, month_str)
            return f"{month_num}/{day}"
        return cleaned

    day = match.group(1)
    month_str = match.group(2).capitalize()
    year = match.group(3)
    if len(day) == 1:
        day = "0" + day
    month_num = MONTH_MAP.get(month_str, month_str)
    return f"{year}-{month_num}-{day}"


def clean_percentage(raw: str) -> str:
    """Clean percentage string."""
    if not raw:
        return ""
    cleaned = raw.replace(" ", "").strip()
    match = re.search(r"[\d]+\.?\d*%?", cleaned)
    return match.group() if match else cleaned


def is_header_row(row_data: list) -> bool:
    """Check if a row is a column header row (not actual data)."""
    text = " ".join(str(x).lower() for x in row_data)
    header_keywords = ["fecha", "descripción", "monto", "saldo", "pago",
                       "movimiento", "tasa", "interés", "cargo"]
    return sum(1 for kw in header_keywords if kw in text) >= 2


def is_total_row(row_data: list) -> bool:
    """Check if a row is a summary/total row (e.g. 'Total cargos', 'Total abonos')."""
    text = " ".join(str(x).lower() for x in row_data)
    return "total cargos" in text or "total abonos" in text


def parse_total_row(row_data: list) -> tuple[str, str] | None:
    """
    Extract total type and amount from a total row.
    Returns ('cargos', amount_str) or ('abonos', amount_str), or None.
    """
    if not is_total_row(row_data):
        return None
    text = " ".join(str(x).lower() for x in row_data)
    kind = "cargos" if "total cargos" in text else "abonos"
    amount_str = ""
    for i in range(len(row_data) - 1, -1, -1):
        val = str(row_data[i]).strip() if i < len(row_data) else ""
        cleaned = clean_amount(val)
        if looks_numeric(cleaned):
            amount_str = cleaned
            break
    if not amount_str:
        return None
    return (kind, amount_str)


_OCR_DIGIT_CONFUSIONS = [
    ("1", "7"), ("0", "6"), ("6", "8"), ("3", "8"), ("5", "6"),
    ("4", "9"), ("2", "7"), ("1", "4"), ("0", "8"),
]


def _amount_str_diff_one_digit(a: str, b: str) -> bool:
    """True if a and b differ by exactly one digit (OCR confusion)."""
    def norm(s: str) -> str:
        s = s.strip()
        if "." in s:
            return s
        return s + ".00" if re.search(r"\d", s) else s
    a, b = norm(a), norm(b)
    if len(a) != len(b):
        return False
    diffs = [(i, a[i], b[i]) for i in range(len(a)) if a[i] != b[i]]
    if len(diffs) != 1:
        return False
    _, x, y = diffs[0]
    return (x, y) in _OCR_DIGIT_CONFUSIONS or (y, x) in _OCR_DIGIT_CONFUSIONS


def reconcile_totals_and_fix(
    df: pd.DataFrame,
    total_cargos: float | None,
    total_abonos: float | None,
    monto_col: str = "Monto",
    tipo_col: str = "Tipo",
) -> list[tuple[int, str, str]]:
    """
    Compare sum of cargos/abonos to expected totals. If a single transaction
    differs by one digit (OCR confusion) and fixing it matches the sum,
    correct that cell in-place and return [(row_index, old_value, new_value), ...].
    """
    if df.empty or monto_col not in df.columns or tipo_col not in df.columns:
        return []
    corrections: list[tuple[int, str, str]] = []
    numeric_monto = pd.to_numeric(df[monto_col], errors="coerce").fillna(0.0)

    for tipo_val, expected in [("Cargo", total_cargos), ("Abono", total_abonos)]:
        if expected is None:
            continue
        mask = df[tipo_col] == tipo_val
        amounts = numeric_monto.loc[mask]
        current_sum = amounts.sum()
        diff = expected - current_sum
        if abs(diff) < 0.01:
            continue
        candidates: list[tuple[int, float, float, float]] = []
        for idx in amounts.index.tolist():
            amt = float(amounts.loc[idx])
            candidate = amt + diff
            if candidate < 0:
                continue
            a_str = f"{amt:.2f}"
            c_str = f"{candidate:.2f}"
            if _amount_str_diff_one_digit(a_str, c_str):
                rel_change = abs(diff / amt) if amt else float("inf")
                candidates.append((idx, amt, candidate, rel_change))
        if candidates:
            candidates.sort(key=lambda x: x[3])
            idx, amt, candidate, _ = candidates[0]
            old_val = str(df.at[idx, monto_col])
            new_val = f"{candidate:.2f}"
            df.at[idx, monto_col] = new_val
            corrections.append((int(idx), old_val, new_val))
            numeric_monto.loc[idx] = candidate
    return corrections


def clean_msi_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean MSI table data."""
    df["Fecha de la operación"] = df["Fecha de la operación"].apply(clean_date)
    df["Monto original"] = df["Monto original"].apply(clean_amount)
    df["Saldo pendiente"] = df["Saldo pendiente"].apply(clean_amount)
    df["Pago requerido"] = df["Pago requerido"].apply(clean_amount)
    df["Tasa de interés aplicable"] = df["Tasa de interés aplicable"].apply(clean_percentage)
    return df


REGULAR_FINAL_COLUMNS = [
    "Fecha Transacción", "Fecha Cargo", "Descripción", "Monto", "Tipo",
    "Tipo Tarjeta", "De quien", "Comentario",
]


def clean_regular_dataframe(df: pd.DataFrame, card_type: str) -> pd.DataFrame:
    """Clean regular (No a meses) table data and update column structure."""
    df["Fecha Transacción"] = df["Fecha de la operación"].apply(clean_date)
    df["Fecha Cargo"] = df["Fecha de cargo"].apply(clean_date)
    df["Descripción"] = df["Descripción del movimiento"].apply(sanitize_ocr)
    df["Tipo"] = df["Tipo"].apply(lambda x: x.strip() if x else "+")
    df["Tipo"] = df["Tipo"].apply(lambda x: "Abono" if x == "-" else "Cargo")
    df["Monto"] = df["Monto"].apply(clean_amount)
    df["Monto"] = df["Monto"].apply(lambda x: x.lstrip("-") if x else x)
    df["Tipo Tarjeta"] = card_type.capitalize()
    df["De quien"] = ""
    df["Comentario"] = ""
    return df[REGULAR_FINAL_COLUMNS]
