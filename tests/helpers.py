"""Shared fixtures for the control layer tests."""

import tempfile
import unittest
from pathlib import Path
from typing import Iterable


class TemporaryDirectoryTestCase(unittest.TestCase):
    """Test case that provides a fresh, automatically removed working directory."""

    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.work_dir = Path(temporary_directory.name)


def render_ids(book_ids: Iterable[object]) -> bytes:
    """Returns canonical control file bytes with one LF-terminated ID per line.

    Bytes are used on purpose: text-mode writes would turn LF into CRLF on
    Windows and make fixtures non-canonical on that platform only.
    """
    return "".join(f"{book_id}\n" for book_id in book_ids).encode("utf-8")
