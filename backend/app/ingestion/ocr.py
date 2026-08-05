from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import pdfplumber
import pytesseract
from docx import Document as DocxDocument
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDocument:
    """Result of text extraction from a document."""

    pages: list[str]  # Text content per page (index = page number - 1)
    page_count: int
    used_ocr: bool  # True if OCR fallback was used


def extract_text_from_pdf(file_bytes: bytes) -> ExtractedDocument:
    """Extract text from a PDF file.

    Tries direct text extraction via pdfplumber first.
    Falls back to OCR (Tesseract) for scanned/image-based pages.

    Args:
        file_bytes: Raw PDF bytes

    Returns:
        ExtractedDocument with per-page text and metadata
    """
    pages: list[str] = []
    used_ocr = False

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)

        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            # If the page has very little text it's likely a scanned image
            if len(text.strip()) < 50:
                logger.debug(f"Page {i + 1} has sparse text — attempting OCR")
                ocr_text = _ocr_pdf_page(page)
                if ocr_text:
                    text = ocr_text
                    used_ocr = True

            pages.append(text)

    if used_ocr:
        logger.info(f"OCR was used on one or more pages ({page_count} total)")

    return ExtractedDocument(pages=pages, page_count=page_count, used_ocr=used_ocr)


def _ocr_pdf_page(page: pdfplumber.page.Page) -> str:
    """Run Tesseract OCR on a single pdfplumber page.

    Args:
        page: pdfplumber page object

    Returns:
        OCR-extracted text, or empty string on failure
    """
    try:
        # Render page to image at 300 DPI for good OCR accuracy
        img = page.to_image(resolution=300).original
        if not isinstance(img, Image.Image):
            img = Image.fromarray(img)
        text: str = pytesseract.image_to_string(img, lang="eng")
        return text.strip()
    except Exception as exc:
        logger.warning(f"OCR failed for page: {exc}")
        return ""


def extract_text_from_docx(file_bytes: bytes) -> ExtractedDocument:
    """Extract text from a DOCX file.

    DOCX files don't have native page boundaries, so all text is
    returned as a single 'page'. Section headings are preserved.

    Args:
        file_bytes: Raw DOCX bytes

    Returns:
        ExtractedDocument with text content
    """
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    full_text = "\n".join(paragraphs)

    return ExtractedDocument(
        pages=[full_text],
        page_count=1,  # DOCX has no native page count without rendering
        used_ocr=False,
    )
