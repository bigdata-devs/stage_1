import logging
import random
from typing import Callable, Optional, Set

from src.control.state_manager import StateManager

logger = logging.getLogger(__name__)


class PipelineController:
    """Coordinates the data ingestion pipeline.

    Decides, at each step, whether a downloaded book should be indexed or a
    new book should be downloaded, ensuring the workflow never duplicates
    work or loses track of progress.
    """

    def __init__(
        self,
        state_manager: StateManager,
        downloader_fn: Optional[Callable[[str], bool]] = None,
        indexer_fn: Optional[Callable[[str], bool]] = None,
        max_book_id: int = 70000,
        max_download_attempts: int = 10,
    ):
        self.state_manager = state_manager
        self.downloader_fn = downloader_fn
        self.indexer_fn = indexer_fn
        self.max_book_id = max_book_id
        self.max_download_attempts = max_download_attempts

    def run_step(self) -> bool:
        """Executes a single pipeline decision step.

        Indexing pending books always takes priority over downloading new
        ones, so the datalake never grows faster than the datamart can
        process it.
        """
        pending_books = self.state_manager.get_pending_indexing_books()
        if pending_books:
            return self._index_one_book(pending_books)
        return self._download_one_new_book()

    def run_loop(self, steps: int = 5) -> None:
        """Runs the control pipeline for a fixed number of steps."""
        logger.info(f"[CONTROL] Starting pipeline loop ({steps} steps)...")
        for step_number in range(1, steps + 1):
            logger.info(f"--- STEP {step_number}/{steps} ---")
            self.run_step()

    def _index_one_book(self, pending_books: Set[str]) -> bool:
        """Sends one pending book to the indexer and updates its state."""
        book_id = pending_books.pop()
        logger.info(f"[CONTROL] Scheduling book {book_id} for indexing...")

        if not self._call_indexer(book_id):
            return False

        self.state_manager.mark_as_indexed(book_id)
        logger.info(f"[CONTROL] Book {book_id} successfully indexed.")
        return True

    def _download_one_new_book(self) -> bool:
        """Finds a book ID not yet downloaded and downloads it."""
        book_id = self._find_new_book_id()
        if book_id is None:
            logger.warning("[CONTROL] No valid download candidate found after retries.")
            return False

        logger.info(f"[CONTROL] Downloading new book with ID {book_id}...")
        if not self._call_downloader(book_id):
            return False

        self.state_manager.mark_as_downloaded(book_id)
        logger.info(f"[CONTROL] Book {book_id} successfully downloaded.")
        return True

    def _find_new_book_id(self) -> Optional[str]:
        """Picks a random book ID that has not been downloaded yet."""
        downloaded_books = self.state_manager.get_downloaded_books()
        for _ in range(self.max_download_attempts):
            candidate_id = str(random.randint(1, self.max_book_id))
            if candidate_id not in downloaded_books:
                return candidate_id
        return None

    def _call_indexer(self, book_id: str) -> bool:
        """Invokes the injected indexer function, if any."""
        return self.indexer_fn(book_id) if self.indexer_fn else True

    def _call_downloader(self, book_id: str) -> bool:
        """Invokes the injected downloader function, if any."""
        return self.downloader_fn(book_id) if self.downloader_fn else True
