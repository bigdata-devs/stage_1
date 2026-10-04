"""Domain vocabulary shared by every chart module.

Holds the results container handed to each chart, the chart contract, how benchmark
tests are named, ordered and grouped into pipeline stages, and the comparability rules
that decide which languages may be compared on a given test.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

LANGUAGE_ORDER = ("python", "java", "go", "rust")
CORE_METRICS = ("benchmarks", "disk_usage", "recovery", "scalability", "statistics", "throughput")
MIN_LANGUAGES_PER_TEST = 2  # a "comparison" with one language is not a comparison


class ChartDataError(Exception):
    """Raised when a chart has no usable data; the orchestrator skips that chart."""


@dataclass(frozen=True)
class BenchmarkResults:
    """Preprocessed benchmark tables, one long DataFrame per metric with a `language` column.

    `metrics` keeps every clean row (the appendix CSV); `comparable` keeps only the tests that
    at least MIN_LANGUAGES_PER_TEST languages measured, and is what every chart reads.
    """

    metrics: Mapping[str, pd.DataFrame]
    comparable: Mapping[str, pd.DataFrame]
    languages: tuple[str, ...]

    def comparable_metric(self, name: str) -> pd.DataFrame:
        frame = self.comparable.get(name, pd.DataFrame())
        if frame.empty:
            raise ChartDataError(f"No '{name}' test was measured by {MIN_LANGUAGES_PER_TEST}+ languages.")
        return frame


class BenchmarkChart(ABC):
    """Contract for a chart module: render one family of figures into its own folder."""

    subdirectory = ""

    @abstractmethod
    def render(self, results: BenchmarkResults, output_dir: Path) -> None:
        """Write every figure of this chart family into `output_dir`."""


@dataclass(frozen=True)
class TestStage:
    """A pipeline stage (e.g. 'Datalake writes') that groups related tests into one panel."""

    title: str
    pattern: str

    def includes(self, test_name: str) -> bool:
        return re.search(self.pattern, test_name) is not None


OTHER_TESTS_STAGE = TestStage("Other tests", r".*")

# test_name -> (full label, label inside its stage panel). Order = pipeline order.
TEST_LABELS: dict[str, tuple[str, str]] = {
    "write_throughput_time_based": ("Datalake write · time-based", "Time-based"),
    "write_throughput_book_based": ("Datalake write · book-based", "Book-based"),
    "write_throughput_batch_based": ("Datalake write · batch-based", "Batch-based"),
    "incremental_time_based": ("Incremental update · time-based", "Time-based"),
    "incremental_book_based": ("Incremental update · book-based", "Book-based"),
    "incremental_batch_based": ("Incremental update · batch-based", "Batch-based"),
    "download_write_throughput": ("Download + write", "Download\n+ write"),
    "tokenize_books": ("Tokenize books", "Tokenize\nbooks"),
    "build_postings": ("Build postings", "Build\npostings"),
    "insert_throughput_sqlite": ("Metadata insert · SQLite", "SQLite"),
    "insert_throughput_postgres": ("Metadata insert · PostgreSQL", "PostgreSQL"),
    "insert_throughput_mongo": ("Metadata insert · MongoDB", "MongoDB"),
    "build_json_index": ("Index build · JSON file", "JSON file"),
    "build_folder_index": ("Index build · Folder", "Folder"),
    "build_mongo_index": ("Index build · MongoDB", "MongoDB"),
    "insert_sqlite": ("Metadata insert · SQLite", "SQLite"),
    "insert_postgres": ("Metadata insert · PostgreSQL", "PostgreSQL"),
    "insert_mongo": ("Metadata insert · MongoDB", "MongoDB"),
    "load_json_index": ("Load JSON index", "Load JSON"),
    "update_json_index": ("Index update · JSON file", "JSON file"),
    "update_folder_index": ("Index update · Folder", "Folder"),
    "update_mongo_index": ("Index update · MongoDB", "MongoDB"),
    "lookup_time_based": ("Datalake lookup · time-based", "Time-based"),
    "lookup_book_based": ("Datalake lookup · book-based", "Book-based"),
    "lookup_batch_based": ("Datalake lookup · batch-based", "Batch-based"),
    "query_json_index": ("Index query · JSON file", "JSON file"),
    "query_folder_index": ("Index query · Folder", "Folder"),
    "query_mongo_index": ("Index query · MongoDB", "MongoDB"),
    "query_id_sqlite": ("Metadata query · by ID", "By ID"),
    "query_path_sqlite": ("Metadata query · by path", "By path"),
    "query_author_sqlite": ("Metadata query · by author", "By author"),
}
TOKEN_LABELS = {"json": "JSON", "sqlite": "SQLite", "postgres": "PostgreSQL", "mongo": "MongoDB", "id": "ID"}


def humanize_test_name(test_name: str) -> str:
    words = [TOKEN_LABELS.get(word, word) for word in test_name.split("_")]
    sentence = " ".join(words)
    return sentence[:1].upper() + sentence[1:]


def full_test_label(test_name: str) -> str:
    return TEST_LABELS.get(test_name, (humanize_test_name(test_name), ""))[0]


def short_test_label(test_name: str) -> str:
    return TEST_LABELS.get(test_name, ("", humanize_test_name(test_name)))[1]


def order_tests(test_names: Iterable[str]) -> list[str]:
    """Known tests in pipeline order first, unknown tests alphabetically after them."""
    rank = {name: position for position, name in enumerate(TEST_LABELS)}
    return sorted(set(test_names), key=lambda name: (rank.get(name, len(rank)), name))


def order_languages(languages: Iterable[str]) -> list[str]:
    known_rank = {name: position for position, name in enumerate(LANGUAGE_ORDER)}
    return sorted(set(languages), key=lambda name: (known_rank.get(name, len(known_rank)), name))


def group_tests_by_stage(test_names: Sequence[str], stages: Sequence[TestStage]) -> list[tuple[TestStage, list[str]]]:
    """Assign each test to the first matching stage; unmatched tests go to 'Other tests'."""
    groups: dict[TestStage, list[str]] = {stage: [] for stage in (*stages, OTHER_TESTS_STAGE)}
    for test_name in order_tests(test_names):
        stage = next(stage for stage in groups if stage.includes(test_name))
        groups[stage].append(test_name)
    return [(stage, tests) for stage, tests in groups.items() if tests]


def languages_measuring(frame: pd.DataFrame, test_name: str) -> list[str]:
    """Languages that have at least one valid row for `test_name` (gaps are simply absent)."""
    return order_languages(frame.loc[frame["test_name"] == test_name, "language"])


def languages_in(frame: pd.DataFrame) -> list[str]:
    return order_languages(frame["language"])


def rows_of_multi_language_tests(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop every test that fewer than MIN_LANGUAGES_PER_TEST languages measured
    (e.g. Python-only metadata inserts), so no chart shows a lone, uncompared bar or line."""
    languages_per_test = frame.groupby("test_name")["language"].transform("nunique")
    return frame[languages_per_test >= MIN_LANGUAGES_PER_TEST]


def rows_shared_by_all_languages(frame: pd.DataFrame, key_columns: Sequence[str]) -> pd.DataFrame:
    """Keep rows whose key (e.g. test_name, batch_size) was measured by every language in `frame`.

    Cross-language scores must compare like with like, so language-only experiments
    (e.g. Python's metadata inserts) are dropped here but still drawn in per-test charts.
    """
    languages_per_key = frame.groupby(list(key_columns))["language"].transform("nunique")
    return frame[languages_per_key == frame["language"].nunique()]
