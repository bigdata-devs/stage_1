import logging
from pathlib import Path
from typing import Set, Union

from src.control.book_id import RawBookId, normalize_book_id
from src.control.control_file import ControlFile
from src.utils.paths import CONTROL_DIR

logger = logging.getLogger(__name__)

DOWNLOADED_FILE_NAME = "downloaded_books.txt"
INDEXED_FILE_NAME = "indexed_books.txt"
FAILED_FILE_NAME = "failed_books.txt"


class StateManager:
    """Tracks pipeline progress using plain text control files.

    Persists the sets of downloaded and indexed book identifiers so the
    pipeline can resume without duplicating or losing work. Book IDs that
    can never be downloaded (missing from Project Gutenberg or without the
    START/END markers) are kept in a third file so they are never requested
    again. The control files live in ``<PROJECT_ROOT>/control`` by default,
    whatever the current working directory is. The control
    files are read once (and repaired if needed) when the manager is
    created; afterwards every query is answered from in-memory sets and
    the disk is only touched to append new state.
    """

    def __init__(self, control_dir: Union[str, Path] = CONTROL_DIR):
        self.control_dir = Path(control_dir)
        self.downloaded_file = self.control_dir / DOWNLOADED_FILE_NAME
        self.indexed_file = self.control_dir / INDEXED_FILE_NAME
        self.failed_file = self.control_dir / FAILED_FILE_NAME
        self.control_dir.mkdir(parents=True, exist_ok=True)
        self._downloaded_log = ControlFile(self.downloaded_file)
        self._indexed_log = ControlFile(self.indexed_file)
        self._failed_log = ControlFile(self.failed_file)
        self._downloaded: Set[str] = set()
        self._indexed: Set[str] = set()
        self._pending: Set[str] = set()
        self._failed: Set[str] = set()
        self.reload()

    def reload(self) -> None:
        """Re-reads both control files from disk, repairing them if they are corrupted."""
        self._downloaded_log.repair()
        self._indexed_log.repair()
        self._failed_log.repair()
        self._downloaded = set(self._downloaded_log.read_ids())
        self._indexed = set(self._indexed_log.read_ids())
        self._failed = set(self._failed_log.read_ids())
        self._pending = self._downloaded - self._indexed
        self._warn_about_orphan_indexed_books()
        logger.info("[STATE] Loaded control files downloaded=%d indexed=%d pending=%d failed=%d",
                    len(self._downloaded), len(self._indexed), len(self._pending), len(self._failed))

    def get_downloaded_books(self) -> Set[str]:
        """Returns a copy of the set of book IDs that have been downloaded."""
        return set(self._downloaded)

    def get_indexed_books(self) -> Set[str]:
        """Returns a copy of the set of book IDs that have been indexed."""
        return set(self._indexed)

    def get_pending_indexing_books(self) -> Set[str]:
        """Returns a copy of the book IDs that are downloaded but not yet indexed."""
        return set(self._pending)

    def get_failed_books(self) -> Set[str]:
        """Returns a copy of the book IDs that could not be downloaded and must not be retried."""
        return set(self._failed)

    def is_downloaded(self, book_id: RawBookId) -> bool:
        """Tells, in O(1), whether a book ID has been downloaded."""
        return normalize_book_id(book_id) in self._downloaded

    def is_indexed(self, book_id: RawBookId) -> bool:
        """Tells, in O(1), whether a book ID has been indexed."""
        return normalize_book_id(book_id) in self._indexed

    def is_failed(self, book_id: RawBookId) -> bool:
        """Tells, in O(1), whether a book ID was recorded as impossible to download."""
        return normalize_book_id(book_id) in self._failed

    def mark_as_downloaded(self, book_id: RawBookId) -> None:
        """Records a book ID as downloaded (idempotent).

        Raises:
            InvalidBookIdError: If the ID is not a clean positive number.
        """
        normalized_id = normalize_book_id(book_id)
        if normalized_id in self._downloaded:
            logger.debug("[STATE] Book already marked as downloaded book_id=%s", normalized_id)
            return
        self._downloaded_log.append(normalized_id)
        self._downloaded.add(normalized_id)
        if normalized_id not in self._indexed:
            self._pending.add(normalized_id)
        logger.info("[STATE] Book %s marked as downloaded.", normalized_id)

    def mark_as_indexed(self, book_id: RawBookId) -> None:
        """Records a book ID as indexed (idempotent).

        Raises:
            InvalidBookIdError: If the ID is not a clean positive number.
        """
        normalized_id = normalize_book_id(book_id)
        if normalized_id in self._indexed:
            logger.debug("[STATE] Book already marked as indexed book_id=%s", normalized_id)
            return
        if normalized_id not in self._downloaded:
            logger.warning("[STATE] Indexing a book that was never downloaded book_id=%s", normalized_id)
        self._indexed_log.append(normalized_id)
        self._indexed.add(normalized_id)
        self._pending.discard(normalized_id)
        logger.info("[STATE] Book %s marked as indexed.", normalized_id)

    def mark_as_failed(self, book_id: RawBookId) -> None:
        """Records a book ID that can never be downloaded, so it is not requested again (idempotent).

        Raises:
            InvalidBookIdError: If the ID is not a clean positive number.
        """
        normalized_id = normalize_book_id(book_id)
        if normalized_id in self._failed:
            logger.debug("[STATE] Book already marked as failed book_id=%s", normalized_id)
            return
        self._failed_log.append(normalized_id)
        self._failed.add(normalized_id)
        logger.info("[STATE] Book %s marked as failed.", normalized_id)

    def _warn_about_orphan_indexed_books(self) -> None:
        """Logs indexed books that do not appear in the downloaded control file."""
        orphan_count = len(self._indexed - self._downloaded)
        if orphan_count:
            logger.warning("[STATE] Inconsistent control files: indexed books missing from downloads count=%d",
                           orphan_count)
