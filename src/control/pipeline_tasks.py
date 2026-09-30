"""Real downloader and indexer callbacks that plug the data layer into the control layer.

The control layer only knows callbacks of the form ``(book_id: str) -> bool``.
This module adapts the datalake and datamart modules to that contract:

* ``DatalakeDownloadTask`` downloads a book into the time-based datalake
  (``datalake/YYYYMMDD/HH/``), the layout recommended by the Stage 1 guide.
* ``BookIndexingTask`` reads that book back from the datalake, stores its
  header metadata and adds its body to the monolithic JSON inverted index.
"""

import logging
from pathlib import Path

from src.datalake.datalake_engine import download_time_based, find_time_based_book
from src.datamarts.inverted_index import json_index
from src.datamarts.metadata.book_metadata import BookMetadata
from src.datamarts.metadata.book_processor import build_book_metadata
from src.datamarts.metadata.storage import MetadataStorage
from src.utils.text_processor import process_text

logger = logging.getLogger(__name__)

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
        metadata = build_book_metadata(find_time_based_book(int(book_id), self.datalake_dir))
        self.metadata_storage.save(metadata)
        logger.info("[INDEXER] Metadata stored book_id=%d title=%r", metadata.book_id, metadata.title)
        self._add_to_inverted_index(metadata)
        return True

    def _add_to_inverted_index(self, metadata: BookMetadata) -> None:
        """Tokenizes the body file and merges its terms into the JSON inverted index."""
        tokens = process_text(metadata.body_path.read_text(encoding=_ENCODING))
        json_index.add_book(metadata.book_id, tokens, self.index_path)
        logger.info("[INDEXER] Inverted index updated book_id=%d tokens=%d", metadata.book_id, len(tokens))
