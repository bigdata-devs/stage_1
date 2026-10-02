"""Tests for the chart suite's loading, cleaning and cross-language comparability rules."""
from pathlib import Path

import pandas as pd
import pytest

from src.visualizations.main import BenchmarkResultsLoader, MetricTableCleaner, METRIC_SCHEMAS, StoragePathClassifier
from src.visualizations.modules.core import languages_measuring, rows_shared_by_all_languages
from src.visualizations.modules.radar_chart import build_radar_table

THROUGHPUT_HEADER = "test_name,item_count,elapsed_seconds,items_per_second,timestamp\n"
STATISTICS_HEADER = "test_name,iterations,mean_seconds,stdev_seconds,min_seconds,max_seconds,timestamp\n"
SCALABILITY_HEADER = "test_name,batch_size,elapsed_seconds,memory_mb,cpu_percent,timestamp\n"
RECOVERY_HEADER = ("test_name,total_books,processed_before_interruption,processed_after_resume,duplicated,lost,"
                   "detection_time,processing_time,elapsed_seconds,timestamp\n")


def write_csv(directory: Path, name: str, content: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content, encoding="utf-8")


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    for language, rate in (("python", 20.0), ("go", 50.0)):
        language_dir = tmp_path / language
        write_csv(language_dir, "throughput.csv", THROUGHPUT_HEADER
                  + f"write_throughput_time_based,100,1.0,{rate},2026-10-02T10:00:00\n")
        write_csv(language_dir, "statistics.csv", STATISTICS_HEADER
                  + f"lookup_time_based,100,{1 / rate},0.00001,0.00001,0.001,2026-10-02T10:00:00\n")
        write_csv(language_dir, "scalability.csv", SCALABILITY_HEADER
                  + f"build_json_index,25,1.0,{rate},{rate + 40},2026-10-02T10:00:00\n")
        write_csv(language_dir, "recovery.csv", RECOVERY_HEADER
                  + f"recovery_time_based,100,50,{50 if language == 'go' else 48},0,"
                  + f"{0 if language == 'go' else 2},0.1,0.1,0.2,2026-10-02T10:00:00\n")
    write_csv(tmp_path / "python", "throughput.csv", THROUGHPUT_HEADER
              + "write_throughput_time_based,100,1.0,20.0,2026-10-02T10:00:00\n"
              + "insert_throughput_sqlite,100,1.0,90.0,2026-10-02T10:00:00\n")
    write_csv(tmp_path / "go", "memstats.csv", "function_name,sys_delta_mb,heap_alloc_delta_mb,total_alloc_mb,"
              "heap_inuse_mb,gc_cycles,timestamp\ntokenize_books,1,1,2,3,4,2026-10-02T10:00:00\n")
    return tmp_path


def test_language_specific_files_are_ignored(results_dir: Path) -> None:
    results = BenchmarkResultsLoader(results_dir).load()
    assert "memstats" not in results.metrics
    assert "memstats" not in results.comparable
    assert set(results.comparable_metric("throughput")["language"]) == {"python", "go"}


def test_single_language_tests_are_kept_for_the_appendix_but_not_charted(results_dir: Path) -> None:
    results = BenchmarkResultsLoader(results_dir).load()
    assert "insert_throughput_sqlite" in set(results.metrics["throughput"]["test_name"])
    assert "insert_throughput_sqlite" not in set(results.comparable_metric("throughput")["test_name"])


def test_missing_metric_files_do_not_stop_loading(results_dir: Path) -> None:
    results = BenchmarkResultsLoader(results_dir).load()
    assert "disk_usage" not in results.metrics
    assert results.languages == ("python", "go")


def test_languages_measuring_lists_only_languages_with_data(results_dir: Path) -> None:
    throughput = BenchmarkResultsLoader(results_dir).load().metrics["throughput"]
    assert languages_measuring(throughput, "insert_throughput_sqlite") == ["python"]
    assert languages_measuring(throughput, "write_throughput_time_based") == ["python", "go"]


def test_shared_rows_exclude_tests_not_run_by_every_language(results_dir: Path) -> None:
    throughput = BenchmarkResultsLoader(results_dir).load().metrics["throughput"]
    shared = rows_shared_by_all_languages(throughput, ["test_name"])
    assert set(shared["test_name"]) == {"write_throughput_time_based"}


def test_cleaner_drops_invalid_rows_and_keeps_latest_measurement() -> None:
    raw = pd.DataFrame({
        "test_name": ["a", "a", "b", "c"],
        "item_count": [1, 1, 1, 1],
        "items_per_second": ["10", "12", "not-a-number", "0"],
        "timestamp": ["2026-10-01", "2026-10-02", "2026-10-02", "2026-10-02"],
    })
    cleaned = MetricTableCleaner().clean(raw, "rust", "throughput", METRIC_SCHEMAS["throughput"])
    assert cleaned["test_name"].tolist() == ["a"]
    assert cleaned["items_per_second"].tolist() == [12.0]


@pytest.mark.parametrize("path, expected", [
    ("/home/u/.cache/stage_1_benchmarks/go/datalake/time_based", ("Datalake", "Time-based")),
    ("/home/u/.cache/stage_1_benchmarks/index/inverted_index.json", ("Index", "JSON file")),
    ("/home/u/.cache/stage_1_benchmarks/rust/datamarts/inverted_index", ("Index", "Folder")),
    ("mongodb://localhost:27017/search_engine_benchmark.inverted_index", ("Index", "MongoDB")),
    ("mongodb://localhost:27017/search_engine_benchmark.books", ("Metadata", "MongoDB")),
    ("host=/var/run/postgresql dbname=bigdata", ("Metadata", "PostgreSQL")),
    ("/home/u/.cache/stage_1_benchmarks/metadata/metadata_benchmark.db", ("Metadata", "SQLite")),
])
def test_storage_paths_are_classified_into_layers(path: str, expected: tuple[str, str]) -> None:
    assert StoragePathClassifier().classify(path) == expected


def test_radar_has_the_five_balanced_axes(results_dir: Path) -> None:
    table = build_radar_table(BenchmarkResultsLoader(results_dir).load())
    assert table.axis_titles == ["Throughput", "Low latency", "CPU efficiency", "Transactional reliability",
                                 "Developer productivity"]


def test_radar_scores_performance_relative_to_the_best_language(results_dir: Path) -> None:
    scores = build_radar_table(BenchmarkResultsLoader(results_dir).load()).scores
    assert scores.loc["go", "Throughput"] == pytest.approx(1.0)
    assert scores.loc["python", "Throughput"] == pytest.approx(0.4)
    assert scores.loc["go", "Low latency"] == pytest.approx(1.0)
    assert scores.loc["python", "CPU efficiency"] == pytest.approx(1.0)


def test_reliability_is_an_absolute_rate_and_productivity_is_hard_coded(results_dir: Path) -> None:
    scores = build_radar_table(BenchmarkResultsLoader(results_dir).load()).scores
    assert scores.loc["go", "Transactional reliability"] == pytest.approx(1.0)
    assert scores.loc["python", "Transactional reliability"] == pytest.approx(0.98)
    assert scores["Developer productivity"].to_dict() == {"python": 1.0, "go": 0.8}
