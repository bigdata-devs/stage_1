import json
import time
import tracemalloc
from pathlib import Path
from statistics import mean, stdev


def measure_time(func, *args, **kwargs) -> float:
    start = time.perf_counter()
    func(*args, **kwargs)
    return time.perf_counter() - start


def measure_memory(func, *args, **kwargs) -> tuple:
    tracemalloc.start()
    result = func(*args, **kwargs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, peak


def measure_disk_usage(file_path: Path) -> int:
    return file_path.stat().st_size


def run_benchmark(func, iterations: int = 5, *args, **kwargs) -> dict:
    times = []
    for _ in range(iterations):
        elapsed = measure_time(func, *args, **kwargs)
        times.append(elapsed)

    return {
        "mean": mean(times),
        "stdev": stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
        "iterations": iterations,
    }


def save_results(results: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_results(results_path: Path) -> dict:
    with open(results_path, "r", encoding="utf-8") as f:
        return json.load(f)
