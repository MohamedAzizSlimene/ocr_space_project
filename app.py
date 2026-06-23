import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests as http_requests
import json_parsing
from groq_parsing import parse_with_groq, parse_pdf_with_groq
from image_utils import compress_image
import pdf_utils

load_dotenv()

app = Flask(__name__)

OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_API_URL = os.getenv("OCR_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FLASK_DEBUG = os.getenv("FLASK_DEBUG")
FLASK_PORT = os.getenv("FLASK_PORT")

logger = logging.getLogger(__name__)


def extract_ocr_text(image_file):
    """Compress the image if needed, then send it to ocr.space and return the parsed text."""
    # ── Pre-process: compress / resize to stay within the API's 1 MB limit ──
    try:
        compressed_buffer, out_filename = compress_image(image_file)
    except ValueError as exc:
        logger.error("Image compression failed: %s", exc)
        return None, 400

    payload = {
        'apikey': OCR_API_KEY,
        'language': 'ara',
        'OCREngine': '3',
        'isTable': 'true'
    }
    files = {
        'file': (out_filename, compressed_buffer, 'image/jpeg')
    }
    response = http_requests.post(OCR_API_URL, data=payload, files=files)

    if response.status_code != 200:
        logger.error("OCR API returned %d: %s", response.status_code, response.text)
        return None, response.status_code

    ocr_result = response.json()
    parsed_text = ocr_result.get("ParsedResults", [{}])[0].get("ParsedText", "")
    return parsed_text, 200


def _is_pdf(file_storage) -> bool:
    """
    Detect whether an uploaded file is a PDF by checking its MIME type
    and filename extension. Uses both signals so it works even when the
    browser sends 'application/octet-stream' for a .pdf file.
    """
    mime = (file_storage.mimetype or "").lower()
    name = (file_storage.filename or "").lower()
    return mime == "application/pdf" or name.endswith(".pdf")


@app.route('/ocr', methods=['POST'])
def ocr_endpoint():
    """Original endpoint - uses rule-based parsing (Tunisian cards)."""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']
    parsed_text, status = extract_ocr_text(image_file)

    if parsed_text is None:
        return jsonify({"error": "OCR API request failed", "status_code": status}), 500

    parsed_data = json_parsing.parse_ocr_response(parsed_text)

    return jsonify({
        "parsed_data": parsed_data,
        "raw_text": parsed_text
    })


@app.route('/arabic/upload/license', methods=['POST'])
def arabic_upload_license():
    """New endpoint - uses Groq LLM for intelligent parsing.

    Accepts either an image file OR a PDF (including scanned PDFs).
    Form fields accepted: 'image' (backward-compatible) or 'file'.

    For scanned PDFs, each page is rendered to a JPEG via PyMuPDF,
    OCR'd individually, and all page texts are joined before being
    sent to Groq — so front + back of a license card are both parsed
    in a single LLM call.
    """
    # Accept 'image' (existing callers) or 'file' (new callers)
    upload = request.files.get('image') or request.files.get('file')
    if upload is None:
        return jsonify({"error": "No file provided. Send under 'image' or 'file' form field."}), 400

    # ── Branch: scanned PDF — render pages → OCR each → join → Groq ─────────
    if _is_pdf(upload):
        pages, status = pdf_utils.render_pdf_pages_to_images(upload)
        if pages is None:
            error_messages = {
                400: "Invalid or corrupted PDF file.",
                422: "PDF contains no pages.",
                500: "Unexpected error while rendering the PDF."
            }
            return jsonify({"error": error_messages.get(status, "PDF processing failed.")}), status

        # OCR every page and collect the texts
        page_texts = []
        for page_image in pages:
            page_text, ocr_status = extract_ocr_text(page_image)
            if page_text is None:
                return jsonify({"error": "OCR failed on one of the PDF pages.", "status_code": ocr_status}), 500
            if page_text.strip():
                page_texts.append(page_text.strip())

        if not page_texts:
            return jsonify({"error": "OCR returned no text from the PDF pages."}), 422

        # Combine all pages into one block — Groq sees the full document
        combined_text = "\n\n--- Page break ---\n\n".join(page_texts)

    # ── Branch: regular image — existing flow unchanged ─────────────────────
    else:
        combined_text, status = extract_ocr_text(upload)
        if combined_text is None:
            return jsonify({"error": "OCR API request failed", "status_code": status}), 500

    # ── Common: send combined text to Groq ───────────────────────────────────
    groq_result = parse_with_groq(combined_text, GROQ_API_KEY)

    return jsonify({
        "groq_parsed": groq_result,
        "raw_text": combined_text
    })



@app.route('/pdf', methods=['POST'])
def pdf_endpoint():
    """Upload and process a PDF document.

    Extracts structured information from identity documents, forms, etc.
    Supports text in Arabic, French, English, or any combination.

    Form field: "pdf" (multipart/form-data)

    Returns:
        JSON with extracted fields:
        - full_name, identification, birth_date, gender
        - mobile, landline, email
        - country, state, address, suite_floor
    """
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file provided. Send the file under the 'pdf' form field."}), 400

    pdf_file = request.files['pdf']

    # Validate MIME type (basic guard — not cryptographic)
    if pdf_file.mimetype not in ('application/pdf', 'application/octet-stream') and \
       not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Uploaded file does not appear to be a PDF."}), 400

    # Extract plain text from all pages
    pdf_text, status = pdf_utils.extract_pdf_text(pdf_file)

    if pdf_text is None:
        error_messages = {
            400: "Invalid or corrupted PDF file.",
            422: "PDF contains no extractable text (may be a scanned image-only PDF).",
            500: "An unexpected error occurred while reading the PDF."
        }
        return jsonify({"error": error_messages.get(status, "PDF processing failed.")}), status

    # Use Groq LLM to extract the structured fields
    extracted_fields = parse_pdf_with_groq(pdf_text, GROQ_API_KEY)

    return jsonify({
        "extracted_fields": extracted_fields,
        "raw_text": pdf_text
    })


if __name__ == '__main__':
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)
