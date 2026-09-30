"""Builds the metadata datamart from the headers already stored in the datalake.

Nothing is downloaded here: the header of every book is read from the
time-based datalake, parsed, normalized and saved together with the paths
of its header and body files.

Usage: python -m src.datamarts.metadata.book_processor
"""

import logging
from datetime import datetime
from pathlib import Path

from src.datalake.datalake_engine import StoredBookFiles, find_time_based_book, list_time_based_books
from src.datamarts.metadata.book_metadata import BookMetadata
from src.datamarts.metadata.header_parser import extract_metadata
from src.datamarts.metadata.storage import MetadataStorage, SQLiteStorage
from src.utils.paths import DATALAKE_DIR

logger = logging.getLogger(__name__)

CAPTURE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_ENCODING = "utf-8"


def build_book_metadata(book_files: StoredBookFiles) -> BookMetadata:
    """Reads and parses the header of a stored book; the capture date is when its header was downloaded."""
    fields = extract_metadata(book_files.header_path.read_text(encoding=_ENCODING))
    return BookMetadata(
        book_id=book_files.book_id,
        title=fields["title"],
        author=fields["author"],
        language=fields["language"],
        capture_date=_read_modification_time(book_files.header_path),
        header_path=book_files.header_path,
        body_path=book_files.body_path,
    )


def process_book(book_id: int, storage: MetadataStorage, datalake_dir: Path = DATALAKE_DIR) -> None:
    """Extracts the metadata of one book from the datalake and saves it.

    Raises:
        FileNotFoundError: If the book is not in the datalake.
    """
    storage.save(build_book_metadata(find_time_based_book(book_id, datalake_dir)))


def process_datalake(storage: MetadataStorage, datalake_dir: Path = DATALAKE_DIR) -> None:
    """Saves (or refreshes) the metadata of every book in the datalake."""
    stored_books = list_time_based_books(datalake_dir)
    for book_files in stored_books.values():
        storage.save(build_book_metadata(book_files))
    logger.info("[METADATA] Stored metadata of %d books from %s", len(stored_books), datalake_dir)


def _read_modification_time(file_path: Path) -> str:
    """Returns the file modification time formatted as a capture date."""
    return datetime.fromtimestamp(file_path.stat().st_mtime).strftime(CAPTURE_DATE_FORMAT)


def main() -> None:
    """Rebuilds ``datamarts/metadata.db`` from every header in the datalake."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    process_datalake(SQLiteStorage())


if __name__ == "__main__":
    main()
