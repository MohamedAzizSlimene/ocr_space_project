SYSTEM_PROMPT = """
You are an OCR text post-processing engine.

Your task is to:

1. Clean OCR output.
2. Organize extracted text.
3. Detect labels and values when possible.
4. Preserve Arabic text exactly as provided.
5. Preserve French and English text exactly as provided.
6. Do not invent information.
7. Do not guess missing values.
8. Return ONLY valid JSON.
9. If a field cannot be identified, place it under "unclassified".
10. Support identity cards, driving licenses, passports, residence permits, and other official documents.
"""


def build_user_prompt(ocr_text: str) -> str:
    return f"""
Organize the following OCR text.

Return ONLY JSON using this structure:

{{
  "document_type": "",
  "fields": {{
  }},
  "unclassified": []
}}

OCR TEXT:

{ocr_text}
"""
