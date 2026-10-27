"""One round of the network download probe: fetch a fresh sample of the corpus and record throughput.

The tournament runs this module once per language per round (five rounds, languages
interleaved round-robin), so every language downloads at the same hours and over the same
network conditions. Keeping it out of the local datalake phase also means Gutenberg latency
never contaminates the write, lookup, incremental and recovery measurements.
"""

import logging
import shutil

from src.datalake.datalake_engine import download_time_based
from src.datalake.errors import BookUnavailableError, TransientDownloadError
from src.utils.benchmarks import (
    calculate_throughput,
    measure_operation,
    save_throughput,
)
from src.utils.benchmarks import data_source
from src.utils.benchmarks.artifacts import ARTIFACT_ROOT

DOWNLOAD_PROBE_COUNT = 10
BENCHMARK_DATA_DIRECTORY = ARTIFACT_ROOT / "datalake"


def run_round() -> list[str]:
    """Downloads the first books of the corpus once and appends one throughput row."""
    try:
        measure_download_throughput(data_source.book_ids())
    except (BookUnavailableError, TransientDownloadError):
        logging.warning("SKIP download_write_throughput: network unavailable")
        return ["download_write_throughput"]
    return []


def measure_download_throughput(book_ids: list[int]) -> None:
    probe_ids = book_ids[:DOWNLOAD_PROBE_COUNT]
    probe_directory = BENCHMARK_DATA_DIRECTORY / "download_probe"
    if probe_directory.exists():
        shutil.rmtree(probe_directory)
    measurement = measure_operation(lambda: download_probe_books(probe_ids, probe_directory))
    stored = measurement.result
    save_throughput({
        "test_name": "download_write_throughput",
        "item_count": stored,
        "elapsed_seconds": measurement.elapsed_seconds,
        "items_per_second": calculate_throughput(stored, measurement.elapsed_seconds),
    })


def download_probe_books(probe_ids: list[int], probe_directory) -> int:
    for book_id in probe_ids:
        download_time_based(book_id, probe_directory)
    return len(probe_ids)


if __name__ == "__main__":
    from src.utils.benchmarks.logging_setup import configure_logging

    configure_logging()
    run_round()
