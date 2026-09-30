"""Runs the Stage 1 data pipeline through the control layer.

Each step either indexes one downloaded book or downloads one new book from
Project Gutenberg, strictly sequentially. Books are stored in the time-based
datalake, their metadata in ``datamarts/metadata.db`` (SQLite) and their
terms in ``datamarts/inverted_index.json``. Every path is anchored to the
project root, so the command can be launched from any directory.

Usage: python -m src.control [--steps N]
"""

import argparse
import logging
from typing import List, Optional

from src.control.pipeline_controller import PipelineController
from src.control.pipeline_tasks import BookIndexingTask, DatalakeDownloadTask
from src.control.state_manager import StateManager
from src.datamarts.metadata.storage import SQLiteStorage
from src.utils.paths import CONTROL_DIR, DATALAKE_DIR, JSON_INDEX_PATH, METADATA_DB_PATH

DEFAULT_STEPS = 10


def parse_arguments(arguments: Optional[List[str]]) -> argparse.Namespace:
    """Reads the command line options."""
    parser = argparse.ArgumentParser(description="Run the Stage 1 download and indexing pipeline.")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS,
                        help=f"number of sequential pipeline steps to run (default: {DEFAULT_STEPS})")
    return parser.parse_args(arguments)


def build_controller(state_manager: StateManager) -> PipelineController:
    """Wires the real datalake downloader and datamart indexer into the controller."""
    downloader = DatalakeDownloadTask(DATALAKE_DIR)
    indexer = BookIndexingTask(DATALAKE_DIR, SQLiteStorage(METADATA_DB_PATH), JSON_INDEX_PATH)
    return PipelineController(state_manager, downloader_fn=downloader.run, indexer_fn=indexer.run)


def print_state_summary(state_manager: StateManager) -> None:
    """Prints the current pipeline state to the console."""
    print("\n=== PIPELINE STATE SUMMARY ===")
    print(f"Downloaded: {len(state_manager.get_downloaded_books())}")
    print(f"Indexed:    {len(state_manager.get_indexed_books())}")
    print(f"Pending:    {sorted(state_manager.get_pending_indexing_books(), key=int)}")
    print(f"Failed:     {len(state_manager.get_failed_books())} (see {state_manager.failed_file})")


def main(arguments: Optional[List[str]] = None) -> None:
    """Runs the pipeline for the requested number of steps and prints the resulting state."""
    options = parse_arguments(arguments)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    state_manager = StateManager(CONTROL_DIR)
    build_controller(state_manager).run_loop(steps=options.steps)
    print_state_summary(state_manager)


if __name__ == "__main__":
    main()
