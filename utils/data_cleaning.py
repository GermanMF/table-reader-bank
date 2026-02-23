"""
Data cleaning and table classification utilities.
"""

import re
import pandas as pd

def classify_table(header_text: str) -> tuple:
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
    """Clean monetary amount: '$21,098.00' -> '21098.00'"""
    if not raw:
        return ""
    cleaned = raw.replace("$", "").replace(",", "").replace(" ", "").strip()
    # Common OCR substitutions for numbers
    cleaned = cleaned.replace("O", "0").replace("o", "0")
    # Extract first valid number pattern
    match = re.search(r"-?[\d]+\.?\d*", cleaned)
    return match.group() if match else cleaned

def _sanitize_ocr(raw: str) -> str:
    """Strip common border-bleed artefacts and normalise whitespace."""
    # Remove border characters that the cell crop sometimes catches
    cleaned = re.sub(r"[\[\]|\\]", " ", raw)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


# Known month abbreviations (Spanish + OCR variants)
_MONTHS = r"(?:Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)"

def clean_date(raw: str) -> str:
    """
    Clean date string and fix common OCR errors.

    Handles:
      - Border bleed: '[17-Ene-2026 |' -> '17-Ene-2026'
      - Day digit misreads: '2f-Ene' (7->f) -> '27-Ene'
      - Extra digit noise: '298-Ene' -> '29-Ene'
      - Single-digit day from clipped glyph: '2-Ene' left as-is
    """
    if not raw:
        return ""

    cleaned = _sanitize_ocr(raw)

    # Fix 'f' misread as '7' in day position: '2f' -> '27'
    cleaned = re.sub(r"\b(\d)f(-" + _MONTHS + r")", r"\g<1>7\2", cleaned, flags=re.IGNORECASE)

    # Fix '/' misread as '7' in day position: '2/' -> '27'  (same glyph, different OCR output)
    cleaned = re.sub(r"\b(\d)/(-" + _MONTHS + r")", r"\g<1>7\2", cleaned, flags=re.IGNORECASE)

    # Fix extra trailing digit on two-digit day: '298-Ene' -> '29-Ene', '187-' -> '18-'
    # Pattern: three digits followed by '-Month' — keep first two digits
    cleaned = re.sub(r"\b(\d{2})\d(-" + _MONTHS + r")", r"\1\2", cleaned, flags=re.IGNORECASE)

    # Now try to extract the date pattern DD-Month-YYYY (day 1–31, year 4 digits)
    match = re.search(
        r"(\d{1,2})-(" + _MONTHS[3:-1] + r")-(\d{4})",  # strip outer (?:)
        cleaned, flags=re.IGNORECASE
    )
    if not match:
        # Fallback: try without year (some cells only show day-month)
        match = re.search(
            r"(\d{1,2})-(" + _MONTHS[3:-1] + r")",
            cleaned, flags=re.IGNORECASE
        )
        if match:
            return f"{match.group(1)}-{match.group(2).capitalize()}"
        return cleaned  # return whatever we have

    day = match.group(1)
    month = match.group(2).capitalize()
    year = match.group(3)

    # Zero-pad single-digit days
    if len(day) == 1:
        day = "0" + day

    return f"{day}-{month}-{year}"

def clean_percentage(raw: str) -> str:
    """Clean percentage string: '0%' -> '0%'"""
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
    return any(kw in text for kw in ["total cargos", "total abonos", "total"])

def clean_msi_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean MSI table data."""
    df["Fecha de la operación"] = df["Fecha de la operación"].apply(clean_date)
    df["Monto original"] = df["Monto original"].apply(clean_amount)
    df["Saldo pendiente"] = df["Saldo pendiente"].apply(clean_amount)
    df["Pago requerido"] = df["Pago requerido"].apply(clean_amount)
    df["Tasa de interés aplicable"] = df["Tasa de interés aplicable"].apply(
        clean_percentage
    )
    return df

def clean_regular_dataframe(df: pd.DataFrame, card_type: str) -> pd.DataFrame:
    """Clean regular (No a meses) table data and update column structure."""
    df["Fecha Transacción"] = df["Fecha de la operación"].apply(clean_date)
    df["Fecha Cargo"] = df["Fecha de cargo"].apply(clean_date)
    df["Descripción"] = df["Descripción del movimiento"].apply(_sanitize_ocr)
    
    # Process "Tipo" (+ is Cargo, - is Abono)
    df["Tipo"] = df["Tipo"].apply(lambda x: x.strip() if x else "+")
    df["Tipo"] = df["Tipo"].apply(lambda x: "Abono" if x == "-" else "Cargo")
    
    # Clean amounts (remove any stray - signs from amount since Tipo handles sign)
    df["Monto"] = df["Monto"].apply(clean_amount)
    df["Monto"] = df["Monto"].apply(lambda x: x.lstrip("-") if x else x)
    
    # Add new columns
    df["Tipo Tarjeta"] = card_type.capitalize()
    df["De quien"] = ""
    df["Comentario"] = ""
    
    # Select and reorder to matching the exact required headers
    final_cols = [
        "Fecha Transacción", 
        "Fecha Cargo", 
        "Descripción", 
        "Monto", 
        "Tipo", 
        "Tipo Tarjeta", 
        "De quien", 
        "Comentario"
    ]
    return df[final_cols]
