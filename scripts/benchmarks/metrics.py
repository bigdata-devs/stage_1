import csv
import time
import logging
from pathlib import Path
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO)

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_FILE = RESULTS_DIR / "benchmarks.csv"

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time

        logging.info(f"[{func.__name__}] executed in {elapsed_time:.4f} seconds")
        save_result(func.__name__, elapsed_time)

        return result
    return wrapper


def save_result(func_name, elapsed):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = RESULTS_FILE.exists()

    with open(RESULTS_FILE, "a", newline="") as results_file:
        writer = csv.writer(results_file)
        if not file_exists:
            writer.writerow(["function_name", "elapsed_seconds", "timestamp"])
        writer.writerow([func_name, f"{elapsed:.6f}", datetime.now().isoformat()])