"""Validation and normalization of Project Gutenberg book identifiers."""

import re
from typing import Union

_NUMERIC_ID_PATTERN = re.compile(r"[0-9]+")

RawBookId = Union[str, int]


class InvalidBookIdError(ValueError):
    """Raised when a value cannot be interpreted as a positive numeric book ID."""


def normalize_book_id(raw_book_id: RawBookId) -> str:
    """Returns the canonical string form of a book ID (e.g. ' 0042 ' -> '42').

    Raises:
        InvalidBookIdError: If the value is not a clean, positive, ASCII numeric ID.
    """
    candidate = str(raw_book_id).strip()
    if not _NUMERIC_ID_PATTERN.fullmatch(candidate):
        raise InvalidBookIdError(f"Book ID must be a numeric string, got {raw_book_id!r}.")
    if int(candidate) == 0:
        raise InvalidBookIdError(f"Book ID must be a positive integer, got {raw_book_id!r}.")
    return str(int(candidate))


def is_valid_book_id(raw_book_id: RawBookId) -> bool:
    """Tells whether a value can be normalized into a valid book ID."""
    try:
        normalize_book_id(raw_book_id)
    except InvalidBookIdError:
        return False
    return True
