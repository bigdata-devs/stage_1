import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class StateManager:
    """Tracks pipeline progress using plain text control files.

    Persists the sets of downloaded and indexed book identifiers so the
    pipeline can resume without duplicating or losing work.
    """

    def __init__(self, control_dir: str = "control"):
        self.control_dir = Path(control_dir)
        self.downloaded_file = self.control_dir / "downloaded_books.txt"
        self.indexed_file = self.control_dir / "indexed_books.txt"
        self.control_dir.mkdir(parents=True, exist_ok=True)

    def get_downloaded_books(self) -> Set[str]:
        """Returns the set of book IDs that have been downloaded."""
        return self._read_ids(self.downloaded_file)

    def get_indexed_books(self) -> Set[str]:
        """Returns the set of book IDs that have been indexed."""
        return self._read_ids(self.indexed_file)

    def get_pending_indexing_books(self) -> Set[str]:
        """Returns book IDs that are downloaded but not yet indexed."""
        return self.get_downloaded_books() - self.get_indexed_books()

    def mark_as_downloaded(self, book_id: str) -> None:
        """Records a book ID as downloaded."""
        self._append_id(self.downloaded_file, book_id, self.get_downloaded_books())
        logger.info(f"[STATE] Book {book_id} marked as downloaded.")

    def mark_as_indexed(self, book_id: str) -> None:
        """Records a book ID as indexed."""
        self._append_id(self.indexed_file, book_id, self.get_indexed_books())
        logger.info(f"[STATE] Book {book_id} marked as indexed.")

    @staticmethod
    def _read_ids(file_path: Path) -> Set[str]:
        """Reads a control file and returns its non-empty lines as a set."""
        if not file_path.exists():
            return set()
        lines = file_path.read_text(encoding="utf-8").splitlines()
        return {line.strip() for line in lines if line.strip()}

    @staticmethod
    def _append_id(file_path: Path, book_id: str, existing_ids: Set[str]) -> None:
        """Appends a book ID to a control file, skipping duplicates."""
        book_id = str(book_id).strip()
        if book_id in existing_ids:
            return
        with open(file_path, "a", encoding="utf-8") as control_file:
            control_file.write(f"{book_id}\n")
