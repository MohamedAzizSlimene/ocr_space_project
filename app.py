import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests as http_requests
import json_parsing
from groq_parsing import parse_with_groq

load_dotenv()

app = Flask(__name__)

OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_API_URL = os.getenv("OCR_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FLASK_DEBUG = os.getenv("FLASK_DEBUG")
FLASK_PORT = os.getenv("FLASK_PORT")

def extract_ocr_text(image_file):
    """Send image to ocr.space and return the parsed text."""
    payload = {
        'apikey': OCR_API_KEY,
        'language': 'ara',
        'OCREngine': '3',
        'isTable': 'true'
    }
    files = {
        'file': (image_file.filename, image_file.stream, image_file.content_type)
    }
    response = http_requests.post(OCR_API_URL, data=payload, files=files)

    if response.status_code != 200:
        return None, response.status_code

    ocr_result = response.json()
    parsed_text = ocr_result.get("ParsedResults", [{}])[0].get("ParsedText", "")
    return parsed_text, 200


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
    """New endpoint - uses Groq LLM for intelligent parsing (any Arabic document)."""
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['image']
    parsed_text, status = extract_ocr_text(image_file)

    if parsed_text is None:
        return jsonify({"error": "OCR API request failed", "status_code": status}), 500

    # Use Groq LLM to intelligently parse the OCR text
    groq_result = parse_with_groq(parsed_text, GROQ_API_KEY)

    return jsonify({
        "groq_parsed": groq_result,
        "raw_text": parsed_text
    })


if __name__ == '__main__':
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)
