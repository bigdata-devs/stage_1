import logging
import random
from typing import Callable, Optional, Set

from src.control.candidate_pool import DownloadCandidatePool, NoDownloadCandidatesError
from src.control.state_manager import StateManager

logger = logging.getLogger(__name__)

TOTAL_BOOKS = 70000

BookCallback = Callable[[str], bool]


class PipelineController:
    """Coordinates the data ingestion pipeline.

    Decides, at each step, whether a downloaded book should be indexed or a
    new book should be downloaded, ensuring the workflow never duplicates
    work or loses track of progress. Execution is strictly sequential: one
    book is processed per step.

    A callback that raises or returns a falsy value counts as a failure:
    the error is logged, the control files are left untouched for that
    book, and the book is not retried again during this controller's
    lifetime (it will be retried on the next run, since it was never
    recorded as done).
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
        if not self._invoke_callback(self.indexer_fn, book_id, "indexer"):
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
        if not self._invoke_callback(self.downloader_fn, book_id, "downloader"):
            return False
        self.state_manager.mark_as_downloaded(book_id)
        logger.info("[CONTROL] Book %s successfully downloaded.", book_id)
        return True

    def _draw_new_book_id(self) -> str:
        """Draws random IDs from the pool until one is not yet downloaded."""
        candidate_pool = self._get_candidate_pool()
        book_id = candidate_pool.draw()
        while self.state_manager.is_downloaded(book_id):
            book_id = candidate_pool.draw()
        return book_id

    def _get_candidate_pool(self) -> DownloadCandidatePool:
        """Builds the pool of untried IDs lazily, on the first download step."""
        if self._candidate_pool is None:
            self._candidate_pool = DownloadCandidatePool(
                self.max_book_id, self.state_manager.get_downloaded_books(), self._random
            )
        return self._candidate_pool

    def _invoke_callback(self, callback: Optional[BookCallback], book_id: str, callback_name: str) -> bool:
        """Runs a stage callback in isolation; a missing callback counts as success."""
        if callback is None:
            return True
        try:
            callback_result = callback(book_id)
        except Exception:
            _log_callback_exception(callback_name, book_id)
            return False
        return _is_successful_result(callback_result, callback_name, book_id)


def _log_callback_exception(callback_name: str, book_id: str) -> None:
    """Logs a callback exception with its traceback."""
    logger.exception("[CONTROL] Callback raised an exception; state left unchanged callback=%s book_id=%s",
                     callback_name, book_id)


def _is_successful_result(callback_result: object, callback_name: str, book_id: str) -> bool:
    """Interprets a callback return value, logging falsy results as failures."""
    if callback_result:
        return True
    logger.error("[CONTROL] Callback reported failure; state left unchanged callback=%s book_id=%s result=%r",
                 callback_name, book_id, callback_result)
    return False


def _require_positive_int(parameter_name: str, value: int) -> None:
    """Raises ValueError unless the value is an integer greater than zero."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{parameter_name} must be a positive integer, got {value!r}.")


def _require_non_negative_int(parameter_name: str, value: int) -> None:
    """Raises ValueError unless the value is an integer greater than or equal to zero."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{parameter_name} must be a non-negative integer, got {value!r}.")
