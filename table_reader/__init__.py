"""
Table Reader — Extract transactions from credit card statement PDFs.

Santander-focused pipeline: OCR, classify MSI vs No a meses, export CSV/Excel
and per-person Resumen.
"""

__all__ = [
    "process_pdf",
    "export_csv",
    "export_excel",
    "build_summary",
]

from table_reader.extraction import process_pdf
from table_reader.export import export_csv, export_excel
from table_reader.summary import build_summary
