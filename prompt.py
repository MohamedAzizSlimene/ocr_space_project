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


# ---------------------------------------------------------------------------
# PDF-specific prompt — extracts a fixed schema of 11 fields
# ---------------------------------------------------------------------------

PDF_SYSTEM_PROMPT = """
You are a multilingual document information extraction engine.

The document text you receive may be written in Arabic, French, English, or a mix of all three.

Your rules:
1. Extract ONLY the fields listed by the user. Do not add extra fields.
2. If a field is not found, return null for that field. NEVER invent or guess a value.
3. Normalize the value to a clean, readable string (remove label prefixes, colons, extra whitespace).
4. For Arabic names, preserve the original Arabic script exactly.
5. For dates, preserve the format as found in the document.
6. For phone numbers, preserve the original format including country code if present.
7. Return ONLY valid JSON — no markdown, no explanation, no code fences.

Field label variants to recognize across languages:

| Canonical field  | Arabic labels                                      | French labels                              | English labels              |
|------------------|----------------------------------------------------|--------------------------------------------|-----------------------------||
| full_name        | الاسم الكامل، الاسم واللقب، الاسم، اللقب          | Nom complet, Nom et prénom, Prénom et Nom  | Full name, Name             |
| identification   | رقم الهوية، رقم البطاقة، رقم الوثيقة، الرقم الوطني | Numéro d'identification, N° CIN, N° pièce | ID number, Document number  |
| birth_date       | تاريخ الميلاد، تاريخ الولادة                       | Date de naissance                          | Date of birth, Birth date   |
| gender           | الجنس، النوع                                        | Sexe, Genre                                | Gender, Sex                 |
| mobile           | الهاتف المحمول، الجوال، رقم الهاتف                 | Téléphone mobile, GSM, Mobile              | Mobile, Cell phone          |
| landline         | الهاتف الثابت، هاتف المنزل                          | Téléphone fixe, Fixe                       | Landline, Phone             |
| email            | البريد الإلكتروني                                   | E-mail, Courriel, Adresse électronique     | Email, E-mail               |
| country          | الدولة، البلد                                       | Pays                                       | Country                     |
| state            | الولاية، المحافظة، المنطقة                          | Gouvernorat, Wilaya, État, Région          | State, Province, Region     |
| address          | العنوان، الشارع                                     | Adresse, Rue                               | Address, Street             |
| suite_floor      | الطابق، الشقة، رقم المبنى                           | Appartement, Étage, Bâtiment              | Suite, Floor, Apt           |
"""


def build_pdf_user_prompt(pdf_text: str) -> str:
    return f"""
Extract information from the following document text.

Return ONLY this JSON structure (use null for any field not found):

{{
  "full_name": null,
  "identification": null,
  "birth_date": null,
  "gender": null,
  "mobile": null,
  "landline": null,
  "email": null,
  "country": null,
  "state": null,
  "address": null,
  "suite_floor": null
}}

DOCUMENT TEXT:

{pdf_text}
"""
