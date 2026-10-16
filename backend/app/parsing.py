"""Extract plain text from uploaded résumé files.

Supports PDF, DOCX, and plain text. Keeps the parsing layer small and
dependency-light: pypdf for PDFs, python-docx for Word files.
"""

from __future__ import annotations

import io
import os
import re

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class UnsupportedFileTypeError(ValueError):
    """Raised when the uploaded file extension is not supported."""


class EmptyDocumentError(ValueError):
    """Raised when no readable text could be extracted."""


def extract_text(filename: str, data: bytes) -> str:
    """Extract and normalize text from an uploaded file's raw bytes."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. Upload a PDF, DOCX, or TXT file."
        )

    if ext == ".pdf":
        text = _extract_pdf(data)
    elif ext == ".docx":
        text = _extract_docx(data)
    else:
        text = _extract_txt(data)

    text = _normalize(text)
    if not text:
        raise EmptyDocumentError("Could not extract any text from the uploaded file.")
    return text


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _extract_txt(data: bytes) -> str:
    # Try UTF-8 first, fall back to latin-1 so we never blow up on encoding.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _normalize(text: str) -> str:
    """Collapse excessive whitespace while preserving line structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
