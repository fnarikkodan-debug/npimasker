"""Detect spans of PII within free text: regex for structured data,
spaCy NER for person names anywhere in a string (e.g. "...his name is
Kang Li").
"""

import re

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b")

_REGEX_DETECTORS = [EMAIL_RE, SSN_RE, DATE_RE]

_nlp = None


def _get_nlp():
    """Lazily load the spaCy model so app startup stays fast when this
    module's detection isn't needed for a given run."""
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not spans:
        return []
    spans = sorted(spans)
    merged = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def find_pii_spans(text: str) -> list[tuple[int, int]]:
    """Return non-overlapping (start, end) spans of detected PII in text."""
    if not text:
        return []

    spans = []
    for pattern in _REGEX_DETECTORS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))

    nlp = _get_nlp()
    for ent in nlp(text).ents:
        if ent.label_ == "PERSON":
            spans.append((ent.start_char, ent.end_char))

    return _merge_spans(spans)
