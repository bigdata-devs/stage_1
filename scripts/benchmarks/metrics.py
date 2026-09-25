import csv
import time
import logging
import psutil
from pathlib import Path
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO)

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_FILE = RESULTS_DIR / "benchmarks.csv"

BYTES_PER_MB = 1024 * 1024


def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time

        logging.info(f"[{func.__name__}] executed in {elapsed_time:.4f} seconds")
        wrapper.last_elapsed = elapsed_time

        return result
    return wrapper


def measure_memory(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        memory_before = process.memory_info().rss
        result = func(*args, **kwargs)
        memory_after = process.memory_info().rss

        consumed_mb = max(memory_after - memory_before, 0) / BYTES_PER_MB

        logging.info(f"[{func.__name__}] consumed {consumed_mb:.4f} MB of RAM")
        wrapper.last_memory_mb = consumed_mb

        return result
    return wrapper


def measure_cpu_usage(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        process.cpu_percent()
        result = func(*args, **kwargs)
        cpu_percent = process.cpu_percent()

        logging.info(f"[{func.__name__}] used {cpu_percent:.2f}% CPU")
        wrapper.last_cpu_percent = cpu_percent

        return result
    return wrapper


def measure_disk_usage(path):
    root = Path(path)

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    total_bytes = 0
    file_count = 0
    dir_count = 0

    for item in root.rglob("*"):
        if item.is_file():
            total_bytes += item.stat().st_size
            file_count += 1
        elif item.is_dir():
            dir_count += 1

    total_mb = total_bytes / BYTES_PER_MB

    logging.info(f"[{root.name}] {total_mb:.4f} MB, {file_count} files, {dir_count} directories")

    return {
        "path": str(root),
        "size_mb": round(total_mb, 4),
        "file_count": file_count,
        "dir_count": dir_count,
    }


def calculate_throughput(item_count, elapsed_seconds):
    if elapsed_seconds <= 0:
        raise ValueError("Elapsed seconds must be greater than zero")
    if item_count < 0:
        raise ValueError("Item count cannot be negative")

    items_per_second = item_count / elapsed_seconds

    logging.info(f"[throughput] {item_count} items in {elapsed_seconds:.4f}s = {items_per_second:.4f} items/s")

    return round(items_per_second, 4)


def save_result(func_name, elapsed, memory_mb, cpu_percent):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = RESULTS_FILE.exists()

    with open(RESULTS_FILE, "a", newline="") as results_file:
        writer = csv.writer(results_file)
        if not file_exists:
            writer.writerow(["function_name", "elapsed_seconds", "memory_mb", "cpu_percent", "timestamp"])
        writer.writerow([func_name, f"{elapsed:.6f}", f"{memory_mb:.4f}", f"{cpu_percent:.2f}", datetime.now().isoformat()])


def save_disk_usage(stats):
    disk_usage_file = RESULTS_DIR / "disk_usage.csv"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = disk_usage_file.exists()

    with open(disk_usage_file, "a", newline="") as results_file:
        writer = csv.writer(results_file)
        if not file_exists:
            writer.writerow(["path", "size_mb", "file_count", "dir_count", "timestamp"])
        writer.writerow([
            stats["path"],
            f"{stats['size_mb']:.4f}",
            stats["file_count"],
            stats["dir_count"],
            datetime.now().isoformat(),
        ])


def save_throughput(test_name, item_count, elapsed_seconds, items_per_second):
    throughput_file = RESULTS_DIR / "throughput.csv"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = throughput_file.exists()

    with open(throughput_file, "a", newline="") as results_file:
        writer = csv.writer(results_file)
        if not file_exists:
            writer.writerow(["test_name", "item_count", "elapsed_seconds", "items_per_second", "timestamp"])
        writer.writerow([
            test_name,
            item_count,
            f"{elapsed_seconds:.6f}",
            f"{items_per_second:.4f}",
            datetime.now().isoformat(),
        ])


def save_scalability(test_name, batch_size, elapsed, memory_mb, cpu_percent):
    scalability_file = RESULTS_DIR / "scalability.csv"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = scalability_file.exists()

    with open(scalability_file, "a", newline="") as results_file:
        writer = csv.writer(results_file)
        if not file_exists:
            writer.writerow(["test_name", "batch_size", "elapsed_seconds", "memory_mb", "cpu_percent", "timestamp"])
        writer.writerow([
            test_name,
            batch_size,
            f"{elapsed:.6f}",
            f"{memory_mb:.4f}",
            f"{cpu_percent:.2f}",
            datetime.now().isoformat(),
        ])


def benchmark(func):
    measured_time_func = measure_time(func)
    measured_memory_func = measure_memory(measured_time_func)
    measured_cpu_func = measure_cpu_usage(measured_memory_func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = measured_cpu_func(*args, **kwargs)
        save_result(
            func.__name__,
            measured_time_func.last_elapsed,
            measured_memory_func.last_memory_mb,
            measured_cpu_func.last_cpu_percent,
        )
        return result
    return wrapper
