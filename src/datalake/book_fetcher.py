"""Single entry point to download a Project Gutenberg book and split it into header and body."""

import logging
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus

import requests

from src.datalake.errors import BookUnavailableError, TransientDownloadError

logger = logging.getLogger(__name__)

START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"
GUTENBERG_URL_TEMPLATE = "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
REQUEST_TIMEOUT_SECONDS = 10

_RETRYABLE_CLIENT_ERRORS = frozenset({HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.TOO_MANY_REQUESTS})


@dataclass(frozen=True)
class GutenbergBook:
    """A downloaded book, already split into its header and body."""

    book_id: int
    header: str
    body: str
    source_url: str
    downloaded_at: datetime


def fetch_and_split(book_id: int) -> GutenbergBook:
    """Downloads a book from Project Gutenberg and splits it into header and body.

    Raises:
        BookUnavailableError: If the book does not exist (4xx such as 404) or
            its text lacks the START/END markers.
        TransientDownloadError: On timeouts, connection errors, HTTP 408/429
            or server errors (5xx); the book may be retried later.
    """
    source_url = build_book_url(book_id)
    text = _download_text(book_id, source_url)
    header, body = split_book_text(book_id, text)
    logger.info("[DATALAKE] Book %d downloaded and split url=%s", book_id, source_url)
    return GutenbergBook(book_id, header, body, source_url, datetime.now())


def build_book_url(book_id: int) -> str:
    """Returns the plain-text download URL of a book."""
    return GUTENBERG_URL_TEMPLATE.format(book_id=book_id)


def split_book_text(book_id: int, text: str) -> tuple[str, str]:
    """Returns the stripped header and body of a Gutenberg text, dropping the footer.

    Raises:
        BookUnavailableError: If the START marker is missing, or no END marker follows it.
    """
    if START_MARKER not in text:
        raise BookUnavailableError(f"Book {book_id} has no Project Gutenberg START marker.")
    header, body_and_footer = text.split(START_MARKER, 1)
    if END_MARKER not in body_and_footer:
        raise BookUnavailableError(f"Book {book_id} has no Project Gutenberg END marker after its START marker.")
    body = body_and_footer.split(END_MARKER, 1)[0]
    return header.strip(), body.strip()


def _download_text(book_id: int, source_url: str) -> str:
    """Performs the HTTP request and returns the response text of a successful download."""
    try:
        response = requests.get(source_url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as network_error:
        raise TransientDownloadError(f"Book {book_id} could not be downloaded: {network_error}") from network_error
    _raise_for_failed_status(book_id, response.status_code)
    return response.text


def _raise_for_failed_status(book_id: int, status_code: int) -> None:
    """Classifies non-200 responses as permanent (most 4xx) or transient (408, 429, 5xx and others)."""
    if status_code == HTTPStatus.OK:
        return
    if _is_permanent_client_error(status_code):
        raise BookUnavailableError(f"Book {book_id} is not available on Project Gutenberg (HTTP {status_code}).")
    raise TransientDownloadError(f"Book {book_id} download failed temporarily (HTTP {status_code}).")


def _is_permanent_client_error(status_code: int) -> bool:
    """Tells whether a status code means the book will never be downloadable from that URL."""
    is_client_error = HTTPStatus.BAD_REQUEST <= status_code < HTTPStatus.INTERNAL_SERVER_ERROR
    return is_client_error and status_code not in _RETRYABLE_CLIENT_ERRORS
