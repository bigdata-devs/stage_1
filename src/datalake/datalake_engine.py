"""Stores downloaded books in the datalake using one of three directory layouts.

Every layout writes ``<BOOK_ID>_header.txt`` and ``<BOOK_ID>_body.txt`` below
``DATALAKE_DIR`` (``<PROJECT_ROOT>/datalake``) by default:

* Time-based:  ``datalake/YYYYMMDD/HH/``  (date and hour of the download)
* Book-based:  ``datalake/<BOOK_ID>/``    (plus a ``metadata.json`` file)
* Batch-based: ``datalake/batch_<LOW>_<HIGH>/`` (ranges of ``batch_size`` IDs)

``download_*`` functions fetch the book and store it; ``store_*`` functions
store an already fetched book, so benchmarks can write the same download
into every layout without hitting Project Gutenberg several times.
``find_*`` functions locate one book and ``list_*`` functions return every
complete book (header and body present) of a layout; the pipeline uses the
time-based ones, the benchmarks compare all three.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.datalake.book_fetcher import GutenbergBook, fetch_and_split
from src.utils.atomic_file import write_text_atomically
from src.utils.paths import DATALAKE_DIR

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 1000
BOOK_METADATA_FILE_NAME = "metadata.json"
_BODY_FILE_PATTERN = re.compile(r"(\d+)_body\.txt")
_BATCH_FOLDER_PATTERN = re.compile(r"batch_\d+_\d+")


@dataclass(frozen=True)
class StoredBookFiles:
    """Location of the header and body files of one book inside the datalake."""

    book_id: int
    header_path: Path
    body_path: Path


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


def find_time_based_book(book_id: int, datalake_dir: Path = DATALAKE_DIR) -> StoredBookFiles:
    """Returns the files of the most recent time-based download of a book.

    ``YYYYMMDD/HH`` folder names sort chronologically, so the last match is
    the newest download.

    Raises:
        FileNotFoundError: If the datalake has no complete (header + body) copy of the book.
    """
    for body_path in sorted(Path(datalake_dir).glob(f"*/*/{body_file_name(book_id)}"), reverse=True):
        header_path = body_path.with_name(header_file_name(book_id))
        if header_path.is_file():
            return StoredBookFiles(book_id, header_path, body_path)
    raise FileNotFoundError(f"No header and body files for book {book_id} in datalake {datalake_dir}")


def find_book_based_book(book_id: int, datalake_dir: Path = DATALAKE_DIR) -> StoredBookFiles:
    """Returns the files of a book in the book-based layout; the folder is derived from the ID, so no scan is needed.

    Raises:
        FileNotFoundError: If the folder does not hold both the header and the body.
    """
    return _require_complete_book(book_based_directory(datalake_dir, book_id), book_id)


def find_batch_based_book(book_id: int, datalake_dir: Path = DATALAKE_DIR, batch_size: int = DEFAULT_BATCH_SIZE) -> StoredBookFiles:
    """Returns the files of a book in the batch-based layout; the range folder is derived from the ID.

    Raises:
        FileNotFoundError: If the range folder does not hold both the header and the body.
    """
    return _require_complete_book(batch_based_directory(datalake_dir, book_id, batch_size), book_id)


def list_time_based_books(datalake_dir: Path = DATALAKE_DIR) -> dict[int, StoredBookFiles]:
    """Returns the newest complete time-based copy of every book in the datalake, keyed by book ID."""
    return _collect_complete_books(Path(datalake_dir).glob("*/*/*_body.txt"))


def list_book_based_books(datalake_dir: Path = DATALAKE_DIR) -> dict[int, StoredBookFiles]:
    """Returns every complete book stored in its own ``<BOOK_ID>/`` folder, keyed by book ID."""
    body_paths = Path(datalake_dir).glob("*/*_body.txt")
    return _collect_complete_books(path for path in body_paths if _is_in_own_book_folder(path))


def list_batch_based_books(datalake_dir: Path = DATALAKE_DIR) -> dict[int, StoredBookFiles]:
    """Returns every complete book stored in a ``batch_<LOW>_<HIGH>/`` folder, keyed by book ID."""
    body_paths = Path(datalake_dir).glob("batch_*_*/*_body.txt")
    return _collect_complete_books(path for path in body_paths if _BATCH_FOLDER_PATTERN.fullmatch(path.parent.name))


def _require_complete_book(directory: Path, book_id: int) -> StoredBookFiles:
    """Returns the files of a book in a known folder, or raises if either file is missing."""
    header_path = directory / header_file_name(book_id)
    body_path = directory / body_file_name(book_id)
    if header_path.is_file() and body_path.is_file():
        return StoredBookFiles(book_id, header_path, body_path)
    raise FileNotFoundError(f"No header and body files for book {book_id} in {directory}")


def _collect_complete_books(body_paths: Iterable[Path]) -> dict[int, StoredBookFiles]:
    """Maps book IDs to their files; in sorted order later (newer time-based) copies win."""
    books: dict[int, StoredBookFiles] = {}
    for body_path in sorted(body_paths):
        books.update(_complete_book_at(body_path))
    return books


def _is_in_own_book_folder(body_path: Path) -> bool:
    """Tells whether a body file sits in the folder named after its book, as in ``84/84_body.txt``."""
    folder_name = body_path.parent.name
    return folder_name.isdigit() and body_path.name == body_file_name(int(folder_name))


def _complete_book_at(body_path: Path) -> dict[int, StoredBookFiles]:
    """Returns ``{book_id: files}`` when a body file has its header next to it, otherwise an empty dict."""
    match = _BODY_FILE_PATTERN.fullmatch(body_path.name)
    if not match:
        return {}
    book_id = int(match.group(1))
    header_path = body_path.with_name(header_file_name(book_id))
    if not header_path.is_file():
        return {}
    return {book_id: StoredBookFiles(book_id, header_path, body_path)}


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
    """Writes UTF-8 text atomically, so a crash never leaves a truncated header, body or ``metadata.json``."""
    write_text_atomically(file_path, content)


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
