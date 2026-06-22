import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests
from json_parsing import parse_ocr_response

load_dotenv()

app = Flask(__name__)

OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_API_URL = os.getenv("OCR_API_URL")
OCR_ENGINE = os.getenv("OCR_ENGINE", "3")
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "ara")
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "message": "Arabic OCR API is running. Use POST /ocr to process an image."
    })


@app.route("/ocr", methods=["POST"])
def ocr():
    # Check if file is provided
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Please upload an image using the 'file' field."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    try:
        # Send image to ocr.space API
        response = requests.post(
            OCR_API_URL,
            files={"file": (file.filename, file.read(), file.content_type)},
            headers={"apikey": OCR_API_KEY},
            data={
                "OCREngine": OCR_ENGINE,
                "language": OCR_LANGUAGE
            }
        )

        # Check if the API request was successful
        if response.status_code != 200:
            return jsonify({
                "error": "OCR API request failed.",
                "status_code": response.status_code,
                "details": response.text
            }), 502

        result = response.json()
        parsed = parse_ocr_response(result)
        raw_text = result.get("ParsedResults", [{}])[0].get("ParsedText", "")
        raw_text_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        return jsonify({"parsed": parsed, "raw_text_lines": raw_text_lines, "raw_text": raw_text})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to connect to OCR API.", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
