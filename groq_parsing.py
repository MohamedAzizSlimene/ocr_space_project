import json
from groq import Groq
from prompt import SYSTEM_PROMPT, build_user_prompt, PDF_SYSTEM_PROMPT, build_pdf_user_prompt


def parse_with_groq(ocr_text: str, api_key: str) -> dict:
    """
    Send OCR text to Groq LLM for intelligent parsing.
    Returns a structured dict with document_type, fields, and unclassified.
    """
    client = Groq(api_key=api_key)

    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": build_user_prompt(ocr_text)
            }
        ]
    )

    response_text = chat_completion.choices[0].message.content

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines[1:] if l.strip() != "```"]
        response_text = "\n".join(lines)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        result = {
            "document_type": "unknown",
            "fields": {},
            "unclassified": [response_text],
            "error": "Failed to parse LLM response as JSON"
        }

    return result


def parse_pdf_with_groq(pdf_text: str, api_key: str) -> dict:
    """
    Send extracted PDF text to Groq LLM for structured field extraction.

    Uses a targeted prompt that extracts a fixed schema of 11 fields
    from documents written in Arabic, French, English, or a mix of all three.

    Args:
        pdf_text: Plain text extracted from the PDF (all pages combined).
        api_key:  Groq API key.

    Returns:
        A dict with keys:
            full_name, identification, birth_date, gender,
            mobile, landline, email,
            country, state, address, suite_floor
        Any field not found in the document will have a null / None value.
        On parse error, includes an "error" key with a description.
    """
    client = Groq(api_key=api_key)

    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": PDF_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": build_pdf_user_prompt(pdf_text)
            }
        ]
    )

    response_text = chat_completion.choices[0].message.content

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [l for l in lines[1:] if l.strip() != "```"]
        response_text = "\n".join(lines)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        result = {
            "full_name": None,
            "identification": None,
            "birth_date": None,
            "gender": None,
            "mobile": None,
            "landline": None,
            "email": None,
            "country": None,
            "state": None,
            "address": None,
            "suite_floor": None,
            "error": "Failed to parse LLM response as JSON",
            "raw_llm_response": response_text
        }

    return result
