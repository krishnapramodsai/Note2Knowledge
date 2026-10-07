"""
extractor.py
Handles pulling raw text out of uploaded files:
- .txt / .md (plain text)
- .pdf (text-based PDFs via pypdf)
- .png / .jpg / .jpeg / .webp (images via OCR with pytesseract)

Resilient error handling: if one method fails, falls back gracefully
and surfaces clear advice to the UI rather than crashing.
"""

import io
import os
from pypdf import PdfReader
from PIL import Image
import pytesseract

# Automatically discover Tesseract binary on Windows if not in PATH
def _configure_tesseract():
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for path in common_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True
    return False


def extract_from_txt(file_bytes: bytes) -> str:
    """Extract string content from text or markdown bytes."""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF pages."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_chunks = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_chunks.append(f"--- Page {i + 1} ---\n{page_text.strip()}")
        text = "\n\n".join(text_chunks).strip()

        if not text:
            raise ValueError(
                "No selectable text found in this PDF. It appears to be a scanned "
                "or image-based document without an embedded text layer."
            )
        return text
    except Exception as e:
        if "No selectable text" in str(e):
            raise
        raise ValueError(f"Failed to parse PDF document: {e}") from e


def extract_from_image(file_bytes: bytes) -> str:
    """Extract text from image using Tesseract OCR."""
    _configure_tesseract()
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Convert to RGB if necessary
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image).strip()
        if not text:
            raise ValueError(
                "OCR could not detect readable text in this image. "
                "Ensure good lighting, sharp contrast, and upright orientation."
            )
        return text
    except pytesseract.TesseractNotFoundError:
        raise ValueError(
            "Tesseract OCR is not installed or not in PATH on this machine. "
            "To OCR photos, install Tesseract OCR (https://github.com/UB-Mannheim/tesseract/wiki) "
            "or upload text/PDF notes directly."
        )


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Route to appropriate extractor based on file extension."""
    lower = filename.lower()
    if lower.endswith((".txt", ".md", ".csv", ".log")):
        return extract_from_txt(file_bytes)
    elif lower.endswith(".pdf"):
        return extract_from_pdf(file_bytes)
    elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")):
        return extract_from_image(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: '{filename}'. Supported: .txt, .pdf, .png, .jpg, .jpeg, .md")
