"""
json_parsing.py

Parses raw OCR text from a Tunisian national ID card (بطاقة التعريف الوطنية)
and extracts structured fields into a dictionary.

Uses flexible keyword matching to handle common OCR noise
(extra spaces, broken characters, partial matches).
"""

import re


def normalize_arabic(text):
    """
    Normalize Arabic text by removing diacritics, extra spaces,
    and normalizing common character variations for better matching.
    """
    # Remove Arabic diacritics (tashkeel)
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]', '', text)
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def contains_keyword(line, keywords):
    """
    Check if a line contains any of the given keywords,
    using a flexible approach that handles OCR spacing issues.

    Removes all spaces from both the line and keyword for comparison,
    so 'ا للقب' will match 'اللقب'.
    """
    line_no_spaces = line.replace(" ", "")
    for keyword in keywords:
        keyword_no_spaces = keyword.replace(" ", "")
        if keyword_no_spaces in line_no_spaces:
            return True
    return False


def extract_value_after_keyword(line, keywords):
    """
    Extract the value portion of a line after removing the keyword label.
    Handles OCR noise by trying multiple strategies:
    1. Direct replacement of the keyword (with/without spaces)
    2. Splitting on the keyword pattern
    """
    normalized_line = normalize_arabic(line)

    for keyword in keywords:
        # Strategy 1: Try direct replacement on normalized text
        if keyword in normalized_line:
            value = normalized_line.replace(keyword, "", 1).strip()
            if value:
                return value

        # Strategy 2: Remove spaces from both and find the split point
        line_no_spaces = normalized_line.replace(" ", "")
        keyword_no_spaces = keyword.replace(" ", "")

        if keyword_no_spaces in line_no_spaces:
            # Find where the keyword ends in the original line
            # by matching character by character (ignoring spaces)
            keyword_chars = list(keyword_no_spaces)
            char_idx = 0
            split_pos = 0

            for i, ch in enumerate(normalized_line):
                if ch == ' ':
                    continue
                if char_idx < len(keyword_chars) and ch == keyword_chars[char_idx]:
                    char_idx += 1
                    split_pos = i + 1
                elif char_idx >= len(keyword_chars):
                    break

            if char_idx == len(keyword_chars):
                value = normalized_line[split_pos:].strip()
                if value:
                    return value

    return None


def parse_id_card(parsed_text):
    """
    Parse the raw OCR text from a Tunisian national ID card and extract structured fields.

    Uses flexible keyword detection to handle OCR inconsistencies
    (extra spaces, broken characters, partial matches in Arabic text).

    Args:
        parsed_text (str): The raw ParsedText string from the OCR response,
                           with lines separated by newline characters.

    Returns:
        dict: A dictionary with the following keys:
            - first_name (str or None)
            - last_name (str or None)
            - document_number (str or None)
            - father_name (str or None)
            - place_of_birth (str or None)
            - date_of_birth (str or None)
    """
    result = {
        "first_name": None,
        "last_name": None,
        "document_number": None,
        "father_name": None,
        "place_of_birth": None,
        "date_of_birth": None,
    }

    # Define keyword variants for each field to handle OCR variations
    keywords_map = {
        "last_name": ["اللقب", "للقب"],
        "first_name": ["الاسم", "لاسم"],
        "father_name": ["بن", "ابن"],
        "date_of_birth": ["تاريخ الولادة", "تاريخالولادة"],
        "place_of_birth": ["مكانها", "مكان الولادة"],
    }

    lines = parsed_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for document number (8+ digits standalone or within a line)
        doc_match = re.search(r'\b(\d{8,})\b', line)
        if doc_match and not any(contains_keyword(line, kws) for kws in keywords_map.values()):
            if result["document_number"] is None:
                result["document_number"] = doc_match.group(1)
            continue

        # Check each field's keywords
        for field, keywords in keywords_map.items():
            if result[field] is not None:
                continue
            if contains_keyword(line, keywords):
                value = extract_value_after_keyword(line, keywords)
                if value:
                    # Clean any remaining noise characters
                    value = re.sub(r'^[\s\-:\.]+', '', value).strip()
                    result[field] = value
                break

    return result


def parse_ocr_response(ocr_json_response):
    """
    Extract ParsedText from the full OCR API JSON response and parse it.

    Args:
        ocr_json_response (dict): The full JSON response from the OCR API.

    Returns:
        dict: A structured dictionary with extracted ID card fields.
    """
    parsed_text = ocr_json_response["ParsedResults"][0]["ParsedText"]
    return parse_id_card(parsed_text)