"""Default keyword list used to detect sensitive CSV columns by header name.

Edit SENSITIVE_KEYWORDS to add/remove fields the tool should treat as
sensitive by default. Matching is case-insensitive and looks for whole
keyword phrases inside the (normalized) header text.
"""

import re

SENSITIVE_KEYWORDS = [
    # name
    "name", "first name", "last name", "full name", "middle name",
    "patient name", "provider name",
    # email
    "email", "e-mail",
    # phone
    "phone", "mobile", "fax", "contact number", "telephone",
    # address
    "address", "street", "city", "state", "zip", "zipcode", "postal",
    # ssn / tax id
    "ssn", "social security", "tax id", "ein",
    # date of birth
    "dob", "date of birth", "birth date", "birthdate",
    # npi / medical / insurance
    "npi", "medical record", "mrn", "insurance", "member id", "policy number",
]


def _normalize(header: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]", " ", header.strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def is_sensitive_header(header: str) -> bool:
    normalized = f" {_normalize(header)} "
    return any(f" {kw} " in normalized for kw in SENSITIVE_KEYWORDS)


def detect_sensitive_columns(headers: list[str]) -> list[int]:
    """Return the indices of headers that look sensitive."""
    return [i for i, h in enumerate(headers) if is_sensitive_header(h)]
