import time
import logging
import statistics
import psutil
from pathlib import Path
from functools import wraps
from typing import NamedTuple

BYTES_PER_MB = 1024 * 1024

class Measurement(NamedTuple):
    result: object
    elapsed_seconds: float
    memory_mb: float
    cpu_percent: float

def measure_operation(operation):
    time_func = measure_time(operation)
    memory_func = measure_memory(time_func)
    cpu_func = measure_cpu_usage(memory_func)
    result = cpu_func()
    return Measurement(
        result,
        time_func.last_elapsed,
        memory_func.last_memory_mb,
        cpu_func.last_cpu_percent,
    )

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        logging.info("[%s] executed in %.4f seconds", func.__name__, elapsed_time)
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
        logging.info("[%s] consumed %.4f MB of RAM", func.__name__, consumed_mb)
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
        logging.info("[%s] used %.2f%% CPU", func.__name__, cpu_percent)
        wrapper.last_cpu_percent = cpu_percent
        return result
    return wrapper

def measure_disk_usage(path):
    root = Path(path)
    if root.is_file():
        return file_usage(root)
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    total_bytes, file_count, dir_count = scan_directory(root)
    total_mb = total_bytes / BYTES_PER_MB
    logging.info("[%s] %.4f MB, %d files, %d directories", root.name, total_mb, file_count, dir_count)
    return {
        "path": str(root),
        "size_mb": round(total_mb, 4),
        "file_count": file_count,
        "dir_count": dir_count,
    }

def scan_directory(root):
    total_bytes = 0
    file_count = 0
    dir_count = 0
    for item in root.rglob("*"):
        if item.is_file():
            total_bytes += item.stat().st_size
            file_count += 1
        elif item.is_dir():
            dir_count += 1
    return total_bytes, file_count, dir_count

def file_usage(root):
    size_bytes = root.stat().st_size
    logging.info("[%s] %.4f MB, 1 file, 0 directories", root.name, size_bytes / BYTES_PER_MB)
    return {
        "path": str(root),
        "size_mb": round(size_bytes / BYTES_PER_MB, 4),
        "file_count": 1,
        "dir_count": 0,
    }

def calculate_throughput(item_count, elapsed_seconds):
    if elapsed_seconds <= 0:
        raise ValueError("Elapsed seconds must be greater than zero")
    if item_count < 0:
        raise ValueError("Item count cannot be negative")
    items_per_second = item_count / elapsed_seconds
    logging.info("[throughput] %d items in %.4fs = %.4f items/s", item_count, elapsed_seconds, items_per_second)
    return round(items_per_second, 4)

def calculate_statistics(durations):
    count = len(durations)
    if count == 0:
        raise ValueError("Durations must not be empty")
    return {
        "iterations": count,
        "mean_seconds": statistics.mean(durations),
        "stdev_seconds": statistics.stdev(durations) if count > 1 else 0.0,
        "min_seconds": min(durations),
        "max_seconds": max(durations),
    }
