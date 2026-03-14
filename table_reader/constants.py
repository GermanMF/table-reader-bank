"""
Centralized constants for extraction and OCR.
"""

RENDER_DPI = 300

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

# When OCRing amount cells, restrict to digits and number symbols
AMOUNT_CHAR_WHITELIST = "0123456789.,$- "
