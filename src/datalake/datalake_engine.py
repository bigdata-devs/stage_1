"""Stores downloaded books in the datalake using one of three directory layouts.

Every layout writes ``<BOOK_ID>_header.txt`` and ``<BOOK_ID>_body.txt`` below
``DATALAKE_DIR`` (``<PROJECT_ROOT>/datalake``) by default:

* Time-based:  ``datalake/YYYYMMDD/HH/``  (date and hour of the download)
* Book-based:  ``datalake/<BOOK_ID>/``    (plus a ``metadata.json`` file)
* Batch-based: ``datalake/batch_<LOW>_<HIGH>/`` (ranges of ``batch_size`` IDs)

``download_*`` functions fetch the book and store it; ``store_*`` functions
store an already fetched book, so benchmarks can write the same download
into every layout without hitting Project Gutenberg several times.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.datalake.book_fetcher import GutenbergBook, fetch_and_split
from src.utils.paths import DATALAKE_DIR

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 1000
BOOK_METADATA_FILE_NAME = "metadata.json"
_ENCODING = "utf-8"


def download_time_based(book_id: int, datalake_dir: Path = DATALAKE_DIR) -> None:
    """Downloads a book into ``<datalake_dir>/YYYYMMDD/HH/``.

    Raises:
        BookUnavailableError: If the book does not exist or lacks the Gutenberg markers.
        TransientDownloadError: On network problems or server errors.
    """
    store_time_based(fetch_and_split(book_id), datalake_dir)


def download_book_based(book_id: int, datalake_dir: Path = DATALAKE_DIR) -> None:
    """Downloads a book into ``<datalake_dir>/<BOOK_ID>/``, raising the same errors as ``download_time_based``."""
    store_book_based(fetch_and_split(book_id), datalake_dir)


def download_batch_based(book_id: int, datalake_dir: Path = DATALAKE_DIR, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
    """Downloads a book into ``<datalake_dir>/batch_<LOW>_<HIGH>/``, raising the same errors as ``download_time_based``."""
    store_batch_based(fetch_and_split(book_id), datalake_dir, batch_size)


def store_time_based(book: GutenbergBook, datalake_dir: Path = DATALAKE_DIR) -> None:
    """Writes the header and body of a fetched book into its time-based folder."""
    _write_book_files(book, time_based_directory(datalake_dir, book.downloaded_at))


def store_book_based(book: GutenbergBook, datalake_dir: Path = DATALAKE_DIR) -> None:
    """Writes the header, body and ``metadata.json`` of a fetched book into its own folder."""
    book_directory = book_based_directory(datalake_dir, book.book_id)
    _write_book_files(book, book_directory)
    _write_book_metadata(book, book_directory)


def store_batch_based(book: GutenbergBook, datalake_dir: Path = DATALAKE_DIR, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
    """Writes the header and body of a fetched book into the folder of its ID range."""
    _write_book_files(book, batch_based_directory(datalake_dir, book.book_id, batch_size))


def time_based_directory(datalake_dir: Path, downloaded_at: datetime) -> Path:
    """Returns ``<datalake_dir>/YYYYMMDD/HH`` for a download time."""
    return Path(datalake_dir) / downloaded_at.strftime("%Y%m%d") / downloaded_at.strftime("%H")


def book_based_directory(datalake_dir: Path, book_id: int) -> Path:
    """Returns ``<datalake_dir>/<BOOK_ID>``."""
    return Path(datalake_dir) / str(book_id)


def batch_based_directory(datalake_dir: Path, book_id: int, batch_size: int = DEFAULT_BATCH_SIZE) -> Path:
    """Returns the range folder of a book, e.g. ``batch_1000_1999`` for book 1342 and a batch size of 1000."""
    if batch_size < 1:
        raise ValueError(f"batch_size must be a positive integer, got {batch_size!r}.")
    lower_bound = (book_id // batch_size) * batch_size
    upper_bound = lower_bound + batch_size - 1
    return Path(datalake_dir) / f"batch_{lower_bound}_{upper_bound}"


def header_file_name(book_id: int) -> str:
    """Returns the header file name of a book, e.g. ``1342_header.txt``."""
    return f"{book_id}_header.txt"


def body_file_name(book_id: int) -> str:
    """Returns the body file name of a book, e.g. ``1342_body.txt``."""
    return f"{book_id}_body.txt"


def _write_book_files(book: GutenbergBook, directory: Path) -> None:
    """Writes the header and body files into the folder, creating it if needed."""
    write_text_file(directory / header_file_name(book.book_id), book.header)
    write_text_file(directory / body_file_name(book.book_id), book.body)
    logger.info("[DATALAKE] Book %d stored in %s", book.book_id, directory)


def _write_book_metadata(book: GutenbergBook, directory: Path) -> None:
    """Writes the auxiliary ``metadata.json`` file of the book-based layout."""
    metadata = {
        "book_id": book.book_id,
        "source_url": book.source_url,
        "downloaded_at": book.downloaded_at.isoformat(timespec="seconds"),
        "header_file": header_file_name(book.book_id),
        "body_file": body_file_name(book.book_id),
    }
    write_text_file(directory / BOOK_METADATA_FILE_NAME, json.dumps(metadata, indent=2) + "\n")


def write_text_file(file_path: Path, content: str) -> None:
    """Writes UTF-8 text, creating the parent folder; newlines are not translated, so files match on every OS."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding=_ENCODING, newline="") as output_file:
        output_file.write(content)


def main() -> None:
    """Manual smoke test: downloads a few books into each layout of the real datalake."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("--- Testing the time-based layout ---")
    download_time_based(1342)
    logger.info("--- Testing the book-based layout ---")
    download_book_based(84)
    logger.info("--- Testing the batch-based layout ---")
    download_batch_based(1500)
    download_batch_based(2500)


if __name__ == "__main__":
    main()
