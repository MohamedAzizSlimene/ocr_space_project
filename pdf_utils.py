"""
pdf_utils.py

Utilities for working with PDF files:
  - extract_pdf_text()         : extract embedded text (text-based PDFs)
  - render_pdf_pages_to_images(): render each page as a JPEG (scanned PDFs)
  - SimpleFileStorage          : minimal shim so rendered pages can be fed
                                 into compress_image() without modification

Handles Arabic (RTL), French, and English content.
"""

import io
import fitz  # PyMuPDF


def extract_pdf_text(pdf_file) -> tuple[str, int]:
    """
    Extract plain text from all pages of a PDF file object.

    Args:
        pdf_file: A file-like object (e.g. from Flask's request.files).

    Returns:
        A tuple of (text: str, status_code: int).
        On success, text is the concatenated text from all pages and status_code is 200.
        On failure, text is None and status_code is the appropriate HTTP error code.
    """
    try:
        pdf_bytes = pdf_file.read()

        # Open the PDF from bytes in memory
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        pages_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Use "text" mode which preserves reading order better for RTL text
            page_text = page.get_text("text")
            if page_text.strip():
                pages_text.append(page_text.strip())

        doc.close()

        if not pages_text:
            return None, 422  # Unprocessable Entity — PDF has no extractable text

        full_text = "\n\n".join(pages_text)
        return full_text, 200

    except fitz.FileDataError:
        return None, 400  # Bad Request — not a valid PDF
    except Exception:
        return None, 500


# ---------------------------------------------------------------------------
# Scanned-PDF support
# ---------------------------------------------------------------------------

class SimpleFileStorage:
    """
    Minimal shim that mimics the parts of werkzeug's FileStorage that
    compress_image() actually uses (.read() and .filename), so that
    in-memory JPEG bytes from a rendered PDF page can be passed into
    the existing OCR pipeline without any changes to compress_image().
    """

    def __init__(self, data: bytes, filename: str):
        self._buffer = io.BytesIO(data)
        self.filename = filename

    def read(self) -> bytes:
        self._buffer.seek(0)
        return self._buffer.read()


def render_pdf_pages_to_images(pdf_file) -> tuple[list, int]:
    """
    Render every page of a PDF to a JPEG image.

    Each page is rendered at 300 DPI — high enough for OCR accuracy while
    keeping file sizes manageable. The results are returned as
    SimpleFileStorage objects so they can be fed directly into
    compress_image() and then the OCR API.

    Args:
        pdf_file: A file-like object (e.g. from Flask's request.files).

    Returns:
        (pages, status_code) where *pages* is a list of SimpleFileStorage
        objects (one per PDF page) and *status_code* is 200 on success.
        On failure, pages is None and status_code is the HTTP error code.
    """
    try:
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # 300 DPI gives a good balance of OCR quality vs. file size
            matrix = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
            jpeg_bytes = pix.tobytes("jpeg")
            filename = f"page_{page_num + 1}.jpg"
            pages.append(SimpleFileStorage(jpeg_bytes, filename))

        doc.close()

        if not pages:
            return None, 422  # PDF has no pages

        return pages, 200

    except fitz.FileDataError:
        return None, 400
    except Exception:
        return None, 500
