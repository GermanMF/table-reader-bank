# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-14

### Added
- Core PDF table extraction from bank statements using OCR.
- Data cleaning logic to normalize monetary amounts (removing underscores) and fix OCR misinterpretations.
- Support for categorizing transactions into specialized sheets (e.g., "Meses sin intereses").
- Export functionality to both CSV and Excel formats.
- Comprehensive README and `.env` template for easy configuration.
- Per-person expense summary generation logic.
- Month abbreviation mapping and standardized date output formats (YYYY-MM-DD or MM/DD).
- `TABLE_NAME` configuration for structured references in Google Sheets formulas.
- `pyproject.toml` for modern Python project management.

### Changed
- Refactored project structure into a modular `table_reader` package for better maintainability.
- Generalized the application by replacing Santander-specific references and concrete person names with generic placeholders.
- Updated `main.py` to use the new modular structure.

### Fixed
- OCR misinterpretations of character '/' as '7' in both monetary amounts and general text.
- Standardized date extraction to handle various regional formats reliably.
