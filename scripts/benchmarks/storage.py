import csv
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path(__file__).parent / "results"


def append_timestamped_row(filename, header, row):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RESULTS_DIR / filename
    file_exists = file_path.exists()

    with open(file_path, "a", newline="") as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow([*header, "timestamp"])
        writer.writerow([*row, datetime.now().isoformat()])


def save_result(stats):
    append_timestamped_row("benchmarks.csv", [
        "function_name", "elapsed_seconds", "memory_mb", "cpu_percent",
    ], [
        stats["function_name"],
        f"{stats['elapsed_seconds']:.6f}",
        f"{stats['memory_mb']:.4f}",
        f"{stats['cpu_percent']:.2f}",
    ])


def save_disk_usage(stats):
    append_timestamped_row("disk_usage.csv", [
        "path", "size_mb", "file_count", "dir_count",
    ], [
        stats["path"],
        f"{stats['size_mb']:.4f}",
        stats["file_count"],
        stats["dir_count"],
    ])


def save_throughput(stats):
    append_timestamped_row("throughput.csv", [
        "test_name", "item_count", "elapsed_seconds", "items_per_second",
    ], [
        stats["test_name"],
        stats["item_count"],
        f"{stats['elapsed_seconds']:.6f}",
        f"{stats['items_per_second']:.4f}",
    ])


def save_scalability(stats):
    append_timestamped_row("scalability.csv", [
        "test_name", "batch_size", "elapsed_seconds", "memory_mb", "cpu_percent",
    ], [
        stats["test_name"],
        stats["batch_size"],
        f"{stats['elapsed_seconds']:.6f}",
        f"{stats['memory_mb']:.4f}",
        f"{stats['cpu_percent']:.2f}",
    ])


def save_recovery(stats):
    append_timestamped_row("recovery.csv", [
        "test_name", "total_books", "processed_before_interruption",
        "processed_after_resume", "duplicated", "lost",
        "detection_time", "processing_time", "elapsed_seconds",
    ], [
        stats["test_name"],
        stats["total_books"],
        stats["processed_before_interruption"],
        stats["processed_after_resume"],
        stats["duplicated"],
        stats["lost"],
        f"{stats['detection_time']:.6f}",
        f"{stats['processing_time']:.6f}",
        f"{stats['elapsed_seconds']:.6f}",
    ])
