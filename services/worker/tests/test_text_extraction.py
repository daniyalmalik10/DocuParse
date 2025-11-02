from pathlib import Path

import pytest

from app.text_extraction import extract_text


def test_extract_pdf_returns_text(pdf_file: Path) -> None:
    text = extract_text(str(pdf_file))
    assert isinstance(text, str)
    assert len(text) > 0


def test_extract_docx_returns_text(docx_file: Path) -> None:
    text = extract_text(str(docx_file))
    assert "Jane Doe" in text
    assert "Python" in text


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    bad = tmp_path / "resume.txt"
    bad.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(str(bad))
