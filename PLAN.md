# Arabic OCR Project Plan

## Project Overview

Arabic OCR (Optical Character Recognition) project using the **ocr.space** free API with **Engine 3**, which provides the best accuracy for Arabic text extraction. The backend is built with Flask to handle image uploads and communicate with the OCR API.

---

## Files to Create

| File               | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `PLAN.md`          | Project plan (this file)                                                    |
| `app.py`           | Flask application – accepts image uploads and sends them to ocr.space API   |
| `requirements.txt` | Python dependencies                                                         |

---

## Tech Stack

- **Python** – Backend language
- **Flask** – Web framework for handling uploads and serving results
- **requests** – HTTP library for calling the ocr.space API
- **ocr.space API (Engine 3)** – OCR service optimized for Arabic

---

## API Details

| Parameter   | Value                                  |
|-------------|----------------------------------------|
| Endpoint    | `https://api.ocr.space/parse/image`    |
| API Key     | `K85262074388957`                      |
| OCR Engine  | `3` (best for Arabic)                  |
| Language    | `ara`                                  |

---

## How It Works

1. **User uploads an image** via the Flask web interface.
2. **Flask sends the image** to the ocr.space API (`POST` request with the image file, API key, engine, and language parameters).
3. **API returns extracted Arabic text** in the JSON response.
4. **Result is displayed** to the user on the web page.

---

## Flow Diagram

```
User (Browser)
    │
    ▼
Flask App (app.py)
    │  POST /upload
    ▼
ocr.space API (Engine 3, lang=ara)
    │
    ▼
Extracted Arabic Text → Displayed to User
```
