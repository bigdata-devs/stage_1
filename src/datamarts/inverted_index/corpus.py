"""Loads the books every index builder works on: the cleaned bodies stored in the datalake.

The list of books and the location of each body come from the metadata
datamart (``body_path``), so run ``python -m src.datamarts.metadata.book_processor``
(or the pipeline in ``main.py``) before building an index.
"""

import logging

from src.datamarts.metadata.storage import SearchableMetadataStorage
from src.utils.text_processor import process_text

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"


def load_corpus(metadata_storage: SearchableMetadataStorage) -> dict[int, list[str]]:
    """Returns the normalized tokens of every book registered in the metadata store, keyed by book ID."""
    books = metadata_storage.list_books()
    if not books:
        logger.warning("No books in the metadata store; run 'python -m src.datamarts.metadata.book_processor' first.")
    corpus = {book.book_id: process_text(book.body_path.read_text(encoding=_ENCODING)) for book in books}
    logger.info("Loaded %d books from the datalake", len(corpus))
    return corpus
