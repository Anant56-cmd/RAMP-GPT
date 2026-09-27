"""
Personally Identifiable Information (PII) Redaction Module.
Sanitizes raw query outputs by masking telephone numbers, email addresses,
and dates of birth while preserving partial identifiers for record confirmation.
"""
import re

def sanitize_database_output(raw_output: str, user_query: str = "") -> str:
    """
    Context-aware PII data redaction guardrail.
    Masks customer and employee phone numbers, emails, and birthdates.
    """
    safe_text = str(raw_output)

    # 1. Phone Redaction (Keeps first 2 and last 2 digits visible: 84XXXXXX17)
    safe_text = re.sub(r'\b(\d{2})\d{6}(\d{2})\b', r'\1XXXXXX\2', safe_text)

    # 2. Email Redaction (Keeps first letter and domain: cXXXX@domain.com)
    safe_text = re.sub(r'([a-zA-Z0-9])[a-zA-Z0-9_.+-]*(@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'\1XXXX\2', safe_text)

    # 3. Context-Aware DOB Redaction
    dob_keywords = ["dob", "birth", "born", "age"]
    if any(keyword in user_query.lower() for keyword in dob_keywords):
        safe_text = re.sub(r'\b\d{2}[-/]\d{2}[-/](\d{4})\b', r'**-**-\1', safe_text)

    return safe_text
