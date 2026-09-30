"""Parses the metadata fields of a Project Gutenberg header and normalizes their values.

Header fields look like ``Title: Some title``. A value may continue on the
following indented lines (long titles, several credits), and a field such as
``Author`` may appear more than once.
"""

import re

UNKNOWN_VALUE = "Unknown"
_FIELD_LINE = re.compile(r"([A-Za-z][A-Za-z ]*?):[ \t]*(.*)")
_WHITESPACE_RUN = re.compile(r"\s+")
_LANGUAGE_SEPARATOR = re.compile(r"\s*,\s*|\s+and\s+|\s*;\s*")

LANGUAGE_CODES = {
    "afrikaans": "af", "arabic": "ar", "bulgarian": "bg", "catalan": "ca", "chinese": "zh",
    "czech": "cs", "danish": "da", "dutch": "nl", "english": "en", "esperanto": "eo",
    "finnish": "fi", "french": "fr", "galician": "gl", "german": "de", "greek": "el",
    "greek, ancient (to 1453)": "grc", "hebrew": "he", "hungarian": "hu", "icelandic": "is",
    "irish": "ga", "italian": "it", "japanese": "ja", "korean": "ko", "latin": "la",
    "middle english (1100-1500)": "enm", "norwegian": "no", "old english (ca. 450-1100)": "ang",
    "polish": "pl", "portuguese": "pt", "romanian": "ro", "russian": "ru", "serbian": "sr",
    "spanish": "es", "swedish": "sv", "tagalog": "tl", "welsh": "cy",
}


def extract_metadata(header_text: str) -> dict[str, str]:
    """Returns the normalized ``title``, ``author`` and ``language`` of a header.

    Missing fields become ``"Unknown"``; several authors are joined with ``"; "``.
    """
    fields = parse_header_fields(header_text)
    return {
        "title": _first_value(fields, "title"),
        "author": "; ".join(fields.get("author", [])) or UNKNOWN_VALUE,
        "language": normalize_language(", ".join(fields.get("language", []))),
    }


def parse_header_fields(header_text: str) -> dict[str, list[str]]:
    """Maps each lower-cased field name to its values, joining indented continuation lines with a space."""
    fields: dict[str, list[str]] = {}
    current_values: list[str] = []
    for line in header_text.replace("\r", "").split("\n"):
        current_values = _consume_line(line, fields, current_values)
    return {name: [_collapse_whitespace(value) for value in values] for name, values in fields.items()}


def normalize_language(raw_language: str) -> str:
    """Maps language names to ISO 639 codes, e.g. ``"English"`` -> ``"en"`` and ``"English, French"`` -> ``"en,fr"``.

    Names without a known code are kept in lower case so no information is lost.
    """
    cleaned = _collapse_whitespace(raw_language).lower()
    if not cleaned:
        return UNKNOWN_VALUE
    if cleaned in LANGUAGE_CODES:
        return LANGUAGE_CODES[cleaned]
    codes = [_language_code(name) for name in _LANGUAGE_SEPARATOR.split(cleaned) if name]
    return ",".join(dict.fromkeys(codes))


def _consume_line(line: str, fields: dict[str, list[str]], current_values: list[str]) -> list[str]:
    """Adds one header line to ``fields`` and returns the value list that continuation lines extend."""
    if not line.strip():
        return []
    if line[0].isspace():
        _extend_last_value(current_values, line)
        return current_values
    match = _FIELD_LINE.fullmatch(line.strip())
    if not match:
        return []
    values = fields.setdefault(match.group(1).strip().lower(), [])
    values.append(match.group(2))
    return values


def _extend_last_value(current_values: list[str], continuation_line: str) -> None:
    """Appends an indented continuation line to the value being read, if any."""
    if current_values:
        current_values[-1] = f"{current_values[-1]} {continuation_line.strip()}"


def _first_value(fields: dict[str, list[str]], name: str) -> str:
    """Returns the first non-empty value of a field, or ``"Unknown"``."""
    values = [value for value in fields.get(name, []) if value]
    return values[0] if values else UNKNOWN_VALUE


def _language_code(language_name: str) -> str:
    """Returns the code of one language name; values that already look like codes are kept."""
    if language_name in LANGUAGE_CODES:
        return LANGUAGE_CODES[language_name]
    return language_name


def _collapse_whitespace(value: str) -> str:
    """Trims the value and turns internal whitespace runs into single spaces."""
    return _WHITESPACE_RUN.sub(" ", value).strip()
