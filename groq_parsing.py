import json
from groq import Groq
from prompt import SYSTEM_PROMPT, build_user_prompt


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
