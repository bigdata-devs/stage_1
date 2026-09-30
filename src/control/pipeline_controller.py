import logging
import random
from enum import Enum
from typing import Callable, Optional, Set

from src.control.candidate_pool import DownloadCandidatePool, NoDownloadCandidatesError
from src.control.state_manager import StateManager
from src.datalake.errors import BookUnavailableError, TransientDownloadError

logger = logging.getLogger(__name__)

TOTAL_BOOKS = 70000

BookCallback = Callable[[str], bool]


class CallbackOutcome(Enum):
    """Result of running a downloader or indexer callback for one book."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BOOK_UNAVAILABLE = "book_unavailable"


class PipelineController:
    """Coordinates the data ingestion pipeline.

    Decides, at each step, whether a downloaded book should be indexed or a
    new book should be downloaded, ensuring the workflow never duplicates
    work or loses track of progress. Execution is strictly sequential: one
    book is processed per step.

    A callback that raises or returns a falsy value counts as a failure:
    the error is logged, the book is not retried again during this
    controller's lifetime, and the downloaded/indexed control files are
    left untouched for it. Such failures are treated as transient (for
    example a network error), so the book is retried on the next run.

    A downloader that raises ``BookUnavailableError`` reports a permanent
    failure instead: the ID is recorded in the failed control file and is
    never drawn again, in this run or any later one.
    """

    def __init__(
        self,
        state_manager: StateManager,
        downloader_fn: Optional[BookCallback] = None,
        indexer_fn: Optional[BookCallback] = None,
        max_book_id: int = TOTAL_BOOKS,
        max_download_attempts: int = 10,
    ):
        """Creates the controller.

        ``max_download_attempts`` is kept for backward compatibility only:
        candidates are now drawn from a pool of untried IDs, so no retries
        are needed to find a new book.
        """
        _require_positive_int("max_book_id", max_book_id)
        _require_positive_int("max_download_attempts", max_download_attempts)
        self.state_manager = state_manager
        self.downloader_fn = downloader_fn
        self.indexer_fn = indexer_fn
        self.max_book_id = max_book_id
        self.max_download_attempts = max_download_attempts
        self._random = random.Random()
        self._candidate_pool: Optional[DownloadCandidatePool] = None
        self._failed_indexing_books: Set[str] = set()

    def run_step(self) -> bool:
        """Executes a single pipeline decision step and tells whether it succeeded.

        Indexing pending books always takes priority over downloading new
        ones, so the datalake never grows faster than the datamart can
        process it.
        """
        indexable_books = self._get_indexable_books()
        if indexable_books:
            return self._index_one_book(indexable_books)
        return self._download_one_new_book()

    def run_loop(self, steps: int = 5) -> None:
        """Runs the control pipeline for a fixed number of sequential steps."""
        _require_non_negative_int("steps", steps)
        logger.info("[CONTROL] Starting pipeline loop (%d steps)...", steps)
        successful_steps = 0
        for step_number in range(1, steps + 1):
            logger.info("--- STEP %d/%d ---", step_number, steps)
            successful_steps += int(self.run_step())
        logger.info("[CONTROL] Pipeline loop finished succeeded=%d failed=%d",
                    successful_steps, steps - successful_steps)

    def _get_indexable_books(self) -> Set[str]:
        """Returns pending books, excluding those whose indexing already failed in this run."""
        return self.state_manager.get_pending_indexing_books() - self._failed_indexing_books

    def _index_one_book(self, indexable_books: Set[str]) -> bool:
        """Sends the oldest-numbered pending book to the indexer and updates its state."""
        book_id = min(indexable_books, key=int)
        logger.info("[CONTROL] Scheduling book %s for indexing...", book_id)
        if self._invoke_callback(self.indexer_fn, book_id, "indexer") is not CallbackOutcome.SUCCEEDED:
            self._failed_indexing_books.add(book_id)
            return False
        self.state_manager.mark_as_indexed(book_id)
        logger.info("[CONTROL] Book %s successfully indexed.", book_id)
        return True

    def _download_one_new_book(self) -> bool:
        """Draws a book ID that was never downloaded and downloads it."""
        try:
            book_id = self._draw_new_book_id()
        except NoDownloadCandidatesError:
            logger.warning("[CONTROL] No download candidates left max_book_id=%d", self.max_book_id)
            return False
        logger.info("[CONTROL] Downloading new book with ID %s...", book_id)
        download_outcome = self._invoke_callback(self.downloader_fn, book_id, "downloader")
        if download_outcome is CallbackOutcome.BOOK_UNAVAILABLE:
            self.state_manager.mark_as_failed(book_id)
        if download_outcome is not CallbackOutcome.SUCCEEDED:
            return False
        self.state_manager.mark_as_downloaded(book_id)
        logger.info("[CONTROL] Book %s successfully downloaded.", book_id)
        return True

    def _draw_new_book_id(self) -> str:
        """Draws random IDs from the pool until one was neither downloaded nor recorded as failed."""
        candidate_pool = self._get_candidate_pool()
        book_id = candidate_pool.draw()
        while self._was_already_tried(book_id):
            book_id = candidate_pool.draw()
        return book_id

    def _was_already_tried(self, book_id: str) -> bool:
        """Tells whether a book was already downloaded or permanently failed to download."""
        return self.state_manager.is_downloaded(book_id) or self.state_manager.is_failed(book_id)

    def _get_candidate_pool(self) -> DownloadCandidatePool:
        """Builds the pool of untried IDs lazily, on the first download step."""
        if self._candidate_pool is None:
            already_tried_ids = self.state_manager.get_downloaded_books() | self.state_manager.get_failed_books()
            self._candidate_pool = DownloadCandidatePool(self.max_book_id, already_tried_ids, self._random)
        return self._candidate_pool

    def _invoke_callback(self, callback: Optional[BookCallback], book_id: str, callback_name: str) -> CallbackOutcome:
        """Runs a stage callback in isolation; a missing callback counts as success."""
        if callback is None:
            return CallbackOutcome.SUCCEEDED
        try:
            callback_result = callback(book_id)
        except BookUnavailableError as unavailable_error:
            return _report_unavailable_book(callback_name, book_id, unavailable_error)
        except TransientDownloadError as transient_error:
            return _report_transient_failure(callback_name, book_id, transient_error)
        except Exception:
            _log_callback_exception(callback_name, book_id)
            return CallbackOutcome.FAILED
        return _interpret_callback_result(callback_result, callback_name, book_id)


def _report_unavailable_book(callback_name: str, book_id: str, unavailable_error: BookUnavailableError) -> CallbackOutcome:
    """Logs a book that can never be processed and returns the matching outcome."""
    logger.warning("[CONTROL] Book is unavailable and will not be retried callback=%s book_id=%s reason=%s",
                   callback_name, book_id, unavailable_error)
    return CallbackOutcome.BOOK_UNAVAILABLE


def _report_transient_failure(callback_name: str, book_id: str, transient_error: TransientDownloadError) -> CallbackOutcome:
    """Logs a temporary failure (no traceback needed) and returns the matching outcome."""
    logger.warning("[CONTROL] Temporary failure; book will be retried on a later run callback=%s book_id=%s reason=%s",
                   callback_name, book_id, transient_error)
    return CallbackOutcome.FAILED


def _log_callback_exception(callback_name: str, book_id: str) -> None:
    """Logs a callback exception with its traceback."""
    logger.exception("[CONTROL] Callback raised an exception; state left unchanged callback=%s book_id=%s",
                     callback_name, book_id)


def _interpret_callback_result(callback_result: object, callback_name: str, book_id: str) -> CallbackOutcome:
    """Interprets a callback return value, logging falsy results as failures."""
    if callback_result:
        return CallbackOutcome.SUCCEEDED
    logger.error("[CONTROL] Callback reported failure; state left unchanged callback=%s book_id=%s result=%r",
                 callback_name, book_id, callback_result)
    return CallbackOutcome.FAILED


def _require_positive_int(parameter_name: str, value: int) -> None:
    """Raises ValueError unless the value is an integer greater than zero."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{parameter_name} must be a positive integer, got {value!r}.")


def _require_non_negative_int(parameter_name: str, value: int) -> None:
    """Raises ValueError unless the value is an integer greater than or equal to zero."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{parameter_name} must be a non-negative integer, got {value!r}.")
