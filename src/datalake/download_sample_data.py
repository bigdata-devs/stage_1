"""Downloads the small sample dataset used by the tests and by quick evaluations.

Books are written to ``sample_data/bodies/<id>_body.txt`` and
``sample_data/headers/<id>_header.txt``. Usage: python -m src.datalake.download_sample_data
"""

import logging
from pathlib import Path

from src.datalake.book_fetcher import GutenbergBook, fetch_and_split
from src.datalake.datalake_engine import body_file_name, header_file_name, write_text_file
from src.datalake.errors import BookUnavailableError, TransientDownloadError
from src.utils.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

SAMPLE_BOOK_IDS = [1342, 11, 84, 174]
SAMPLE_DATA_PATH = PROJECT_ROOT / "sample_data"


def download_sample_dataset(book_ids: list[int], output_path: Path) -> tuple[list[int], list[int]]:
    """Downloads every book and returns the IDs that succeeded and those that failed."""
    successful: list[int] = []
    failed: list[int] = []
    for book_id in book_ids:
        if _download_sample_book(book_id, output_path):
            successful.append(book_id)
        else:
            failed.append(book_id)
    return successful, failed


def save_book_content(book: GutenbergBook, output_path: Path) -> None:
    """Writes the header and body of a fetched book into the sample dataset folders."""
    write_text_file(output_path / "headers" / header_file_name(book.book_id), book.header)
    write_text_file(output_path / "bodies" / body_file_name(book.book_id), book.body)


def _download_sample_book(book_id: int, output_path: Path) -> bool:
    """Downloads and saves one sample book, logging instead of raising when it fails."""
    try:
        save_book_content(fetch_and_split(book_id), output_path)
    except (BookUnavailableError, TransientDownloadError) as download_error:
        logger.error("[FAIL] Book %d: %s", book_id, download_error)
        return False
    logger.info("[OK] Book %d downloaded successfully", book_id)
    return True


def main() -> None:
    """Downloads the sample dataset into ``sample_data/``."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    successful, failed = download_sample_dataset(SAMPLE_BOOK_IDS, SAMPLE_DATA_PATH)
    logger.info("Results: %d succeeded, %d failed", len(successful), len(failed))


if __name__ == "__main__":
    main()
