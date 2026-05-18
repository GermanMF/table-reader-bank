# Lessons Learned

## 2026-05-18: Total Row Filtering & OCR Amount Corrections

### Bug: "Total de cargos/abonos" rows leaked as transactions
- **Root cause**: `is_total_row()` checked for `"total cargos"` but the actual OCR text was `"Total de cargos"` (with "de" in between).
- **Fix**: Added `"total de cargos"` and `"total de abonos"` patterns to both `is_total_row()` and `parse_total_row()`.

### Bug: Missing decimal point in large OCR amounts
- **Root cause**: OCR sometimes drops the decimal point entirely, producing values like `811351` instead of `8113.51`. The `clean_amount()` function had no logic to re-insert a decimal.
- **Fix**: Added a heuristic in `clean_amount()`: if the result is all digits (no `.`) and ≥4 digits long, insert a decimal 2 places from the end.

### Bug: Per-table footer totals corrupted individual tables
- **Root cause**: The PDF footer totals (e.g. "Total de cargos: $39,718.96") span the entire statement (titular + adicional combined), but were being applied to individual sub-tables as if they were sub-table-specific totals.
- **Fix**: Skip per-table footer reconciliation when `.env` expected totals are configured. The consolidated reconciliation with `.env` values is more reliable.

### Enhancement: Multi-strategy reconciliation
- **Strategy 1**: Single-digit OCR confusion (e.g. '1' ↔ '7') — already existed.
- **Strategy 2** (new): Missing decimal point detection via digit extraction and re-insertion.
- **Strategy 3** (new): Mathematical outlier correction — if one row's replacement with a positive "needed" value fixes the total, apply it. Picks the row with the largest deviation.

### Enhancement: Amount column OCR whitelist
- Applied `AMOUNT_CHAR_WHITELIST` to the amount column (col 4) in `_ocr_regular_row()`, restricting Tesseract to digits/dots/commas to reduce garbage characters.
