"""Manual smoke test for the control layer.

Runs a short pipeline loop with mock downloader/indexer functions so the
control layer's decision logic can be exercised without the real datalake
and datamart components. Usage: python -m src.control
"""

import logging

from src.control.pipeline_controller import PipelineController
from src.control.state_manager import StateManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def mock_downloader(book_id: str) -> bool:
    """Simulates downloading a book instead of calling the real datalake."""
    print(f"  --> [MOCK DOWNLOADER] Downloading Gutenberg ebook ID: {book_id}")
    return True


def mock_indexer(book_id: str) -> bool:
    """Simulates indexing a book instead of calling the real datamart."""
    print(f"  --> [MOCK INDEXER] Building index entry for ID: {book_id}")
    return True


def print_state_summary(state_manager: StateManager) -> None:
    """Prints the current pipeline state to the console."""
    downloaded = state_manager.get_downloaded_books()
    indexed = state_manager.get_indexed_books()
    pending = state_manager.get_pending_indexing_books()

    print("\n=== PIPELINE STATE SUMMARY ===")
    print(f"Downloaded ({len(downloaded)}): {downloaded}")
    print(f"Indexed ({len(indexed)}): {indexed}")
    print(f"Pending ({len(pending)}): {pending}")


def main() -> None:
    """Runs a short pipeline loop using mock downloader/indexer functions."""
    print("=== CONTROL LAYER PIPELINE TEST ===")

    state_manager = StateManager(control_dir="control")
    controller = PipelineController(
        state_manager=state_manager,
        downloader_fn=mock_downloader,
        indexer_fn=mock_indexer,
    )

    controller.run_loop(steps=5)
    print_state_summary(state_manager)


if __name__ == "__main__":
    main()
