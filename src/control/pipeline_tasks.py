"""Real downloader and indexer callbacks that plug the data layer into the control layer.

The control layer only knows callbacks of the form ``(book_id: str) -> bool``.
This module adapts the datalake and datamart modules to that contract:

* ``DatalakeDownloadTask`` downloads a book into the time-based datalake
  (``datalake/YYYYMMDD/HH/``), the layout recommended by the Stage 1 guide.
* ``BookIndexingTask`` reads that book back from the datalake, stores its
  header metadata and adds its body to the monolithic JSON inverted index.
"""

import logging
from datetime import datetime
from pathlib import Path

from src.datalake.datalake_engine import download_time_based
from src.datamarts.inverted_index import json_index
from src.datamarts.metadata.book_processor import extract_metadata
from src.datamarts.metadata.storage import MetadataStorage
from src.utils.text_processor import process_text

logger = logging.getLogger(__name__)

BODY_PART = "body"
HEADER_PART = "header"
CAPTURE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_ENCODING = "utf-8"


class DatalakeDownloadTask:
    """Downloads a Project Gutenberg book and stores its header and body in the time-based datalake."""

    def __init__(self, datalake_dir: Path):
        self.datalake_dir = Path(datalake_dir)

    def run(self, book_id: str) -> bool:
        """Downloads one book.

        Raises:
            BookUnavailableError: If the book does not exist on Project Gutenberg
                or its text lacks the START/END markers.
            TransientDownloadError: On timeouts, network or server errors,
                which the control layer retries on a later run.
        """
        download_time_based(int(book_id), self.datalake_dir)
        return True


class BookIndexingTask:
    """Indexes a downloaded book: header metadata into the metadata store, body into the JSON inverted index."""

    def __init__(self, datalake_dir: Path, metadata_storage: MetadataStorage, index_path: Path):
        self.datalake_dir = Path(datalake_dir)
        self.metadata_storage = metadata_storage
        self.index_path = Path(index_path)

    def run(self, book_id: str) -> bool:
        """Indexes one book; running it twice for the same book leaves the datamarts unchanged.

        Raises:
            FileNotFoundError: If the book is not present in the datalake.
        """
        book_number = int(book_id)
        header_path = find_latest_book_file(self.datalake_dir, book_number, HEADER_PART)
        body_path = find_latest_book_file(self.datalake_dir, book_number, BODY_PART)
        self._store_metadata(book_number, header_path)
        self._add_to_inverted_index(book_number, body_path)
        return True

    def _store_metadata(self, book_number: int, header_path: Path) -> None:
        """Parses the header file and saves its metadata, stamped with the download time."""
        metadata = extract_metadata(header_path.read_text(encoding=_ENCODING))
        metadata["book_id"] = book_number
        metadata["Capture Date"] = _read_modification_time(header_path)
        self.metadata_storage.save(metadata)
        logger.info("[INDEXER] Metadata stored book_id=%d title=%r", book_number, metadata["Title"])

    def _add_to_inverted_index(self, book_number: int, body_path: Path) -> None:
        """Tokenizes the body file and merges its terms into the JSON inverted index."""
        tokens = process_text(body_path.read_text(encoding=_ENCODING))
        json_index.add_book(book_number, tokens, self.index_path)
        logger.info("[INDEXER] Inverted index updated book_id=%d tokens=%d", book_number, len(tokens))


def find_latest_book_file(datalake_dir: Path, book_id: int, part: str) -> Path:
    """Returns the newest ``<book_id>_<part>.txt`` stored in the time-based datalake.

    ``YYYYMMDD/HH`` folder names sort chronologically, so the last match is
    the most recent download.

    Raises:
        FileNotFoundError: If the datalake holds no such file.
    """
    matches = sorted(Path(datalake_dir).glob(f"*/*/{book_id}_{part}.txt"))
    if not matches:
        raise FileNotFoundError(f"No {part} file for book {book_id} in datalake {datalake_dir}")
    return matches[-1]


def _read_modification_time(file_path: Path) -> str:
    """Returns the file modification time, i.e. when the book was downloaded."""
    return datetime.fromtimestamp(file_path.stat().st_mtime).strftime(CAPTURE_DATE_FORMAT)
