"""The metadata record stored for every book, and how its file paths are persisted."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from src.utils.paths import PROJECT_ROOT


@dataclass(frozen=True)
class BookMetadata:
    """Normalized header metadata of a book plus the location of its files in the datalake."""

    book_id: int
    title: str
    author: str
    language: str
    capture_date: str
    header_path: Path
    body_path: Path


class BookNotFoundError(LookupError):
    """Raised when the metadata store has no book with the requested ID."""


def to_stored_path(path: Path) -> str:
    """Serializes a path for the database: relative to the project root (POSIX style) when possible.

    Relative paths keep the database valid when the repository is cloned
    elsewhere or opened from another operating system.
    """
    absolute_path = Path(path).resolve()
    if absolute_path.is_relative_to(PROJECT_ROOT):
        return absolute_path.relative_to(PROJECT_ROOT).as_posix()
    return str(absolute_path)


def resolve_stored_path(stored_path: str) -> Path:
    """Turns a path read from the database back into an absolute path."""
    candidate = Path(stored_path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / PurePosixPath(stored_path)
