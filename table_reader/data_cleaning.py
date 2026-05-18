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
    normalize_month,
    normalize_day,
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
    """Clean common OCR errors in amounts."""
    if not isinstance(raw, str):
        return str(raw)
        
    parts = raw.split()
    if len(parts) >= 2:
        # Tesseract often reads an isolated '$' as '3', '5', 'S', etc. with a space after it.
        if parts[0] in ("3", "5", "S", "s", "1", "o", "O", "8"):
            raw = " ".join(parts[1:])

    cleaned = raw.replace("$", "").replace(" ", "").replace("_", "").strip()
    if cleaned.endswith("]"):
        cleaned = cleaned[:-1]
    if re.search(r",\d{2}(?:\D|$)", cleaned) and cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace("O", "0").replace("o", "0")
    cleaned = cleaned.replace("S", "5").replace("s", "5")
    cleaned = cleaned.replace("l", "1").replace("I", "1")
    cleaned = re.sub(r"(\d)/(\d)", r"\g<1>7\2", cleaned)
    result = first_number(cleaned)
    # If the number is all digits (no decimal) and has 4+ digits,
    # it's likely a missing decimal point — insert one 2 places from end.
    if re.fullmatch(r"\d{4,}", result):
        result = result[:-2] + "." + result[-2:]
    return result


def clean_date(raw: str) -> str:
    """
    Clean date string and fix common OCR errors.
    Handles border bleed, noisy month tokens (e.g. 'Apbr' → 'Abr'),
    garbled day digits (e.g. '2/' → '02'), and extra digit noise.
    """
    if not raw:
        return ""
    cleaned = sanitize_ocr(raw)

    # Broad pattern: capture any word-like month token (letters only) so
    # normalize_month() can fuzzy-match it, and capture the day and year.
    # Allows extra characters in the month string (e.g. 'Apbr', 'Abpr').
    match = re.search(
        r"(\d{1,2}[^-]*)-(\w+)-(\d{4})",
        cleaned, flags=re.IGNORECASE
    )
    if match:
        raw_day, raw_month, year = match.group(1), match.group(2), match.group(3)
        day = normalize_day(raw_day)
        month_canon = normalize_month(raw_month)
        month_num = MONTH_MAP.get(month_canon, None)
        if month_num:
            return f"{year}-{month_num}-{day}"

    # Fallback: try with exact MONTHS_PATTERN (original logic)
    months_inner = MONTHS_PATTERN[3:-1]  # strip (?: and )
    match = re.search(
        r"(\d{1,2})-(" + months_inner + r")-(\d{4})",
        cleaned, flags=re.IGNORECASE
    )
    if match:
        day = match.group(1).zfill(2)
        month_str = match.group(2).capitalize()
        year = match.group(3)
        month_num = MONTH_MAP.get(month_str, month_str)
        return f"{year}-{month_num}-{day}"

    # No year: partial date (month/day only)
    match = re.search(r"(\d{1,2})-(" + months_inner + r")", cleaned, flags=re.IGNORECASE)
    if match:
        day = match.group(1).zfill(2)
        month_str = match.group(2).capitalize()
        month_num = MONTH_MAP.get(month_str, month_str)
        return f"{month_num}/{day}"

    return cleaned


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
    """Check if a row is a summary/total row (e.g. 'Total cargos', 'Total de cargos')."""
    text = " ".join(str(x).lower() for x in row_data)
    return (
        "total cargos" in text
        or "total abonos" in text
        or "total de cargos" in text
        or "total de abonos" in text
    )


def parse_total_row(row_data: list) -> tuple[str, str] | None:
    """
    Extract total type and amount from a total row.
    Returns ('cargos', amount_str) or ('abonos', amount_str), or None.
    """
    if not is_total_row(row_data):
        return None
    text = " ".join(str(x).lower() for x in row_data)
    kind = "cargos" if ("total cargos" in text or "total de cargos" in text) else "abonos"
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


def _try_decimal_insertion(raw_str: str, expected_remainder: float) -> float | None:
    """
    If OCR lost the decimal point, try inserting it at plausible positions.
    Returns corrected float if inserting a decimal in `raw_str` yields
    `expected_remainder`, or None.
    """
    digits = re.sub(r"[^\d]", "", raw_str)
    if len(digits) < 3:
        return None
    for pos in range(len(digits) - 2, max(0, len(digits) - 4), -1):
        candidate_str = digits[:pos] + "." + digits[pos:]
        try:
            val = float(candidate_str)
            if abs(val - expected_remainder) < 0.02:
                return val
        except ValueError:
            continue
    return None


def reconcile_totals_and_fix(
    df: pd.DataFrame,
    total_cargos: float | None,
    total_abonos: float | None,
    monto_col: str = "Monto",
    tipo_col: str = "Tipo",
) -> list[tuple[int, str, str]]:
    """
    Compare sum of cargos/abonos to expected totals. Attempts multiple
    correction strategies:
      1. Single-digit OCR confusion (e.g. '1' ↔ '7').
      2. Missing decimal point (e.g. '81135' → '811.35').
      3. Large outlier replacement when the diff magnitude is close to
         one transaction's value.
    Corrects cells in-place and returns [(row_index, old_value, new_value), ...].
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

        # Strategy 1: single-digit OCR confusion
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
            continue

        # Strategy 2: catastrophic misread (missing decimal, huge outlier)
        # If removing one amount and substituting a corrected value fixes the sum,
        # try decimal insertion or outlier replacement.
        sum_without: dict[int, float] = {}
        for idx in amounts.index.tolist():
            amt = float(amounts.loc[idx])
            sum_without[idx] = current_sum - amt

        best_fix: tuple[int, float, float] | None = None
        best_score = float("inf")
        for idx in amounts.index.tolist():
            amt = float(amounts.loc[idx])
            needed = expected - sum_without[idx]
            if needed <= 0:
                continue
            # Try decimal insertion on the raw string
            raw_val = str(df.at[idx, monto_col])
            fixed = _try_decimal_insertion(raw_val, needed)
            if fixed is not None:
                score = abs(amt - fixed) / max(amt, 1)
                if score < best_score:
                    best_score = score
                    best_fix = (idx, amt, fixed)

        if best_fix is not None:
            idx, amt, fixed = best_fix
            old_val = str(df.at[idx, monto_col])
            new_val = f"{fixed:.2f}"
            df.at[idx, monto_col] = new_val
            corrections.append((int(idx), old_val, new_val))
            numeric_monto.loc[idx] = fixed
            continue

        # Strategy 3: mathematical outlier correction.
        # If exactly one row accounts for the entire discrepancy (i.e. replacing
        # its amount with a positive "needed" value fixes the total), apply it.
        # Pick the row whose current amount deviates most from its needed value.
        outlier_candidates: list[tuple[int, float, float, float]] = []
        for idx in amounts.index.tolist():
            amt = float(amounts.loc[idx])
            needed = expected - sum_without[idx]
            if needed <= 0:
                continue
            deviation = abs(amt - needed)
            # Only consider if the deviation is large enough to matter
            if deviation > 1.0:
                outlier_candidates.append((idx, amt, needed, deviation))
        if outlier_candidates:
            # Pick the row with the largest deviation (most likely OCR error)
            outlier_candidates.sort(key=lambda x: x[3], reverse=True)
            idx, amt, needed, _ = outlier_candidates[0]
            old_val = str(df.at[idx, monto_col])
            new_val = f"{needed:.2f}"
            df.at[idx, monto_col] = new_val
            corrections.append((int(idx), old_val, new_val))
            numeric_monto.loc[idx] = needed

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
