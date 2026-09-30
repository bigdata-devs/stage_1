"""Durable, crash-tolerant storage for a list of book IDs (one per line)."""

import logging
import os
from pathlib import Path
from typing import Dict, List

from src.control.book_id import InvalidBookIdError, normalize_book_id

logger = logging.getLogger(__name__)

_LINE_TERMINATOR = "\n"
_ENCODING = "utf-8"


class ControlFile:
    """Append-only text file that persists one book ID per line.

    Every record is written together with its line terminator in a single
    write, followed by flush + fsync. A final line without a terminator can
    therefore only come from a write interrupted by a crash, so it is treated
    as a torn record and discarded: redoing that book is safer than trusting
    a possibly truncated ID.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def read_ids(self) -> List[str]:
        """Returns the valid, unique IDs stored in the file, in file order."""
        complete_lines = self._read_complete_lines()
        unique_ids: Dict[str, None] = {}
        for line_number, line in enumerate(complete_lines, start=1):
            self._collect_id(line, line_number, unique_ids)
        return list(unique_ids)

    def repair(self) -> None:
        """Rewrites the file in canonical form if it holds invalid or duplicated content."""
        canonical_content = self._render(self.read_ids())
        if self._read_raw_text() == canonical_content:
            return
        logger.warning("[STATE] Repairing control file path=%s", self.path)
        self._replace_atomically(canonical_content)

    def append(self, book_id: str) -> None:
        """Durably appends one (already normalized) book ID to the file."""
        with open(self.path, "a", encoding=_ENCODING, newline=_LINE_TERMINATOR) as control_file:
            control_file.write(f"{book_id}{_LINE_TERMINATOR}")
            control_file.flush()
            os.fsync(control_file.fileno())

    def _collect_id(self, line: str, line_number: int, unique_ids: Dict[str, None]) -> None:
        """Adds the ID found on a line to the accumulator, skipping blank or corrupted lines."""
        if not line.strip():
            return
        try:
            unique_ids[normalize_book_id(line)] = None
        except InvalidBookIdError:
            logger.warning("[STATE] Skipping corrupted line path=%s line=%d content=%r", self.path, line_number, line)

    def _read_complete_lines(self) -> List[str]:
        """Returns the file lines, dropping a trailing line left unterminated by a crash."""
        raw_text = self._read_raw_text()
        lines = raw_text.splitlines()
        if lines and not raw_text.endswith(("\n", "\r")):
            logger.warning("[STATE] Discarding torn last record path=%s content=%r", self.path, lines[-1])
            lines.pop()
        return lines

    def _read_raw_text(self) -> str:
        """Reads the whole file, tolerating undecodable bytes; a missing file reads as empty."""
        if not self.path.exists():
            return ""
        return self.path.read_bytes().decode(_ENCODING, errors="replace")

    def _replace_atomically(self, content: str) -> None:
        """Writes content to a temporary sibling file and atomically swaps it into place."""
        temporary_path = self.path.with_name(f"{self.path.name}.tmp")
        with open(temporary_path, "w", encoding=_ENCODING, newline=_LINE_TERMINATOR) as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, self.path)

    @staticmethod
    def _render(book_ids: List[str]) -> str:
        """Returns the canonical file content for a list of IDs."""
        return "".join(f"{book_id}{_LINE_TERMINATOR}" for book_id in book_ids)
