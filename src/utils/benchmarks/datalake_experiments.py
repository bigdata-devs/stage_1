import logging
import shutil
import time
from pathlib import Path

from src.datalake.errors import BookUnavailableError, TransientDownloadError
from src.utils.benchmarks import (
    measure_operation,
    measure_disk_usage,
    calculate_throughput,
    calculate_statistics,
    save_throughput,
    save_result,
    save_statistics,
    save_recovery,
    save_disk_usage,
)
from src.utils.benchmarks import data_source
from src.utils.benchmarks.artifacts import ARTIFACT_ROOT
from src.utils.benchmarks.datalake_layouts import TimeBasedLayout, BookBasedLayout, BatchBasedLayout
from src.utils.benchmarks.logging_setup import configure_logging
from src.datalake.datalake_engine import download_time_based

BENCHMARK_DATA_DIRECTORY = ARTIFACT_ROOT / "datalake"
DOWNLOAD_PROBE_COUNT = 10
LAYOUTS = [TimeBasedLayout(), BookBasedLayout(), BatchBasedLayout()]

def run():
    book_ids = data_source.book_ids()
    logging.info("Running datalake experiments with %s books", len(book_ids))
    skipped = []
    for layout in LAYOUTS:
        run_layout_experiments(layout, book_ids)
    try:
        measure_download_throughput(book_ids)
    except (BookUnavailableError, TransientDownloadError):
        logging.warning("SKIP download_write_throughput: network unavailable")
        skipped.append("download_write_throughput")
    return skipped

def run_layout_experiments(layout, book_ids):
    logging.info("--- Datalake structure: %s ---", layout.name)
    measure_write_throughput(layout, book_ids)
    measure_lookup(layout, book_ids)
    measure_incremental(layout, book_ids)
    measure_recovery(layout, book_ids)
    measure_storage_overhead(layout)

def measure_write_throughput(layout, book_ids):
    reset_structure_directory(layout)
    measurement = measure_operation(lambda: populate_structure(layout, book_ids))
    save_throughput({
        "test_name": f"write_throughput_{layout.name}",
        "item_count": len(book_ids),
        "elapsed_seconds": measurement.elapsed_seconds,
        "items_per_second": calculate_throughput(len(book_ids), measurement.elapsed_seconds),
    })

def measure_lookup(layout, book_ids):
    base = structure_base(layout)
    durations = []
    for book_id in book_ids:
        start_time = time.perf_counter()
        layout.locate_book(base, book_id)
        durations.append(time.perf_counter() - start_time)
    stats = calculate_statistics(durations)
    stats["test_name"] = f"lookup_{layout.name}"
    save_statistics(stats)

def measure_incremental(layout, book_ids):
    base = structure_base(layout)
    known = set(book_ids[: len(book_ids) // 2])
    measurement = measure_operation(lambda: detect_pending(layout, base, known))
    save_result({
        "function_name": f"incremental_{layout.name}",
        "elapsed_seconds": measurement.elapsed_seconds,
        "memory_mb": measurement.memory_mb,
        "cpu_percent": measurement.cpu_percent,
    })

def measure_storage_overhead(layout):
    save_disk_usage(measure_disk_usage(structure_base(layout)))

def measure_recovery(layout, book_ids):
    stats = resume_after_interruption(layout, book_ids)
    stats["test_name"] = f"recovery_{layout.name}"
    save_recovery(stats)

def measure_download_throughput(book_ids):
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

def resume_after_interruption(layout, book_ids):
    base = structure_base(layout)
    processed = set(book_ids[: len(book_ids) // 2])
    start_time = time.perf_counter()
    pending = detect_pending(layout, base, processed)
    detection_time = time.perf_counter() - start_time
    resumed = process_pending(layout, base, pending)
    processing_time = time.perf_counter() - start_time - detection_time
    duplicated, lost = verify_resume(book_ids, processed, resumed)
    return {
        "total_books": len(book_ids),
        "processed_before_interruption": len(processed),
        "processed_after_resume": len(resumed),
        "duplicated": duplicated,
        "lost": lost,
        "detection_time": detection_time,
        "processing_time": processing_time,
        "elapsed_seconds": time.perf_counter() - start_time,
    }

def detect_pending(layout, base, known_book_ids):
    found = set(layout.list_book_ids(base))
    return sorted(found - known_book_ids)

def process_pending(layout, base, pending_book_ids):
    resumed = []
    for book_id in pending_book_ids:
        stored = layout.locate_book(base, book_id)
        stored.body_path.read_text(encoding="utf-8")
        stored.header_path.read_text(encoding="utf-8")
        resumed.append(book_id)
    return resumed

def verify_resume(book_ids, processed, resumed):
    duplicated = len(set(resumed) & processed)
    lost = len(set(book_ids) - processed - set(resumed))
    return duplicated, lost

def download_probe_books(probe_ids, probe_directory):
    for book_id in probe_ids:
        download_time_based(book_id, probe_directory)
    return len(probe_ids)

def populate_structure(layout, book_ids):
    for book_id in book_ids:
        header = read_source_header(book_id)
        body = read_source_body(book_id)
        layout.store_book(structure_base(layout), book_id, header, body)

def reset_structure_directory(layout):
    base = structure_base(layout)
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    return base

def read_source_header(book_id):
    return (data_source.headers_directory() / f"{book_id}_header.txt").read_text(encoding="utf-8")

def read_source_body(book_id):
    return (data_source.bodies_directory() / f"{book_id}_body.txt").read_text(encoding="utf-8")

def structure_base(layout):
    return BENCHMARK_DATA_DIRECTORY / layout.name

if __name__ == "__main__":
    configure_logging()
    run()
