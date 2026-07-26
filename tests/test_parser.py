"""
Unit tests for parser.py (Document Reader component).

Validates: Requirements 1.2, 1.3, 1.4, 1.5
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parser import extract_text_from_docx, extract_text_from_file


# 5.1 — FileNotFoundError for a non-existent path (Requirement 1.3)
def test_extract_text_from_file_raises_for_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(FileNotFoundError):
        extract_text_from_file(missing)


# 5.2 — ValueError for unsupported extension .txt (Requirement 1.4)
def test_extract_text_from_file_raises_for_txt_extension(tmp_path):
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text("some content")
    with pytest.raises(ValueError):
        extract_text_from_file(txt_file)


# 5.3 — extract_text_from_docx returns non-empty string (Requirement 1.2)
def test_extract_text_from_docx_returns_nonempty_string(sample_docx):
    result = extract_text_from_docx(sample_docx)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


# 5.4 — PDF page with no selectable text yields empty string, no exception (Requirement 1.5)
def test_extract_text_from_file_handles_pdf_page_with_no_text(tmp_path):
    # Create a minimal real file so exists() check passes
    fake_pdf = tmp_path / "empty_page.pdf"
    fake_pdf.write_bytes(b"")  # content doesn't matter; pdfplumber.open is mocked

    mock_page = MagicMock()
    mock_page.extract_text.return_value = None  # simulates a non-selectable page

    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf):
        result = extract_text_from_file(fake_pdf)

    assert result == ""
