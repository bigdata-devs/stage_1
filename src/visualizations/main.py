"""Orchestrator for the benchmark chart suite.

Pipeline:
    1. load      benchmarks_results/<language>/<metric>.csv  (python, go, java, rust); any other
                 CSV (e.g. go/memstats.csv) is language-specific and ignored
    2. clean     standardise columns, coerce numbers, drop incomplete/invalid rows, keep the
                 latest measurement per key, classify storage paths, check recovery integrity
    3. compare   keep only tests measured by 2+ languages for the charts
    4. export    charts/consolidated_metrics.csv (every clean row, for the appendix)
    5. render    every chart module into its own folder: charts/scalability, charts/throughput,
                 charts/latency, charts/sankey, charts/radar

Usage, from the repository root:
    python -m src.visualizations.main
    python src/visualizations/main.py --results-dir benchmarks_results --output-dir charts
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

if __package__ in (None, ""):  # run as a file: make the repository root importable for `src.`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from src.visualizations.modules.core import (CORE_METRICS, BenchmarkChart, BenchmarkResults,  # noqa: E402
                                             ChartDataError, order_languages, rows_of_multi_language_tests)
from src.visualizations.modules.latency_charts import LatencyChart  # noqa: E402
from src.visualizations.modules.radar_chart import ExecutiveRadar  # noqa: E402
from src.visualizations.modules.scalability_charts import ScalabilityCharts  # noqa: E402
from src.visualizations.modules.storage_sankey import StorageSankey  # noqa: E402
from src.visualizations.modules.theme import apply_matplotlib_theme, language_label  # noqa: E402
from src.visualizations.modules.throughput_charts import ThroughputChart  # noqa: E402

LOGGER = logging.getLogger("src.visualizations")


# --------------------------------------------------------------------------- schemas
@dataclass(frozen=True)
class MetricSchema:
    """Columns a metric table must provide. Rows missing a key or numeric value are dropped;
    `positive_columns` must be > 0 (a 0 s latency or 0 items/s is a failed run, not a result)."""

    key_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    positive_columns: tuple[str, ...] = ()


METRIC_SCHEMAS = {
    "benchmarks": MetricSchema(("test_name",), ("elapsed_seconds", "memory_mb", "cpu_percent")),
    "disk_usage": MetricSchema(("path",), ("size_mb", "file_count", "dir_count")),
    "recovery": MetricSchema(("test_name",), ("total_books", "processed_before_interruption",
                                              "processed_after_resume", "duplicated", "lost"), ("total_books",)),
    "scalability": MetricSchema(("test_name", "batch_size"), ("batch_size", "elapsed_seconds", "memory_mb",
                                                              "cpu_percent"), ("batch_size", "elapsed_seconds")),
    "statistics": MetricSchema(("test_name",), ("mean_seconds", "stdev_seconds", "min_seconds", "max_seconds"),
                               ("mean_seconds",)),
    "throughput": MetricSchema(("test_name",), ("item_count", "items_per_second"), ("items_per_second",)),
}
COLUMN_ALIASES = {"function_name": "test_name"}


class SchemaMismatchError(ValueError):
    """A CSV lacks columns its metric requires."""


# --------------------------------------------------------------------------- reading & cleaning
class CsvTableReader:
    """Reads one CSV; an unreadable or empty file becomes an empty table plus a warning."""

    def read(self, path: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(path)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, OSError) as error:
            return self._report_unreadable(path, error)

    @staticmethod
    def _report_unreadable(path: Path, error: Exception) -> pd.DataFrame:
        LOGGER.warning("Skipping unreadable file %s (%s)", path, error)
        return pd.DataFrame()


class MetricTableCleaner:
    """Turns one raw CSV into a validated, language-tagged table."""

    def clean(self, frame: pd.DataFrame, language: str, metric: str, schema: MetricSchema) -> pd.DataFrame:
        if frame.empty:
            return frame
        standardized = self._standardize_columns(frame)
        self._require_columns(standardized, metric, schema)
        tagged = standardized.assign(language=language, metric=metric)
        typed = self._coerce_types(tagged, schema)
        valid = self._drop_invalid_rows(typed, f"{language}/{metric}", schema)
        return self._keep_latest_measurement(valid, schema)

    @staticmethod
    def _standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
        renamed = frame.rename(columns=lambda column: str(column).strip().lower())
        return renamed.rename(columns=COLUMN_ALIASES)

    @staticmethod
    def _require_columns(frame: pd.DataFrame, metric: str, schema: MetricSchema) -> None:
        missing = set(schema.key_columns + schema.numeric_columns) - set(frame.columns)
        if missing:
            raise SchemaMismatchError(f"{metric}.csv is missing columns {sorted(missing)}")

    @staticmethod
    def _coerce_types(frame: pd.DataFrame, schema: MetricSchema) -> pd.DataFrame:
        converted = {column: pd.to_numeric(frame[column], errors="coerce") for column in schema.numeric_columns}
        text_keys = [key for key in schema.key_columns if key not in schema.numeric_columns]
        converted.update({key: frame[key].astype("string").str.strip() for key in text_keys})
        if "timestamp" in frame.columns:
            converted["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        return frame.assign(**converted)

    @staticmethod
    def _drop_invalid_rows(frame: pd.DataFrame, source: str, schema: MetricSchema) -> pd.DataFrame:
        required = list(schema.key_columns + schema.numeric_columns)
        complete = frame.dropna(subset=required)
        valid = complete[(complete[list(schema.positive_columns)] > 0).all(axis=1)]
        if len(valid) < len(frame):
            LOGGER.warning("%s: dropped %d incomplete or non-positive rows", source, len(frame) - len(valid))
        return valid

    @staticmethod
    def _keep_latest_measurement(frame: pd.DataFrame, schema: MetricSchema) -> pd.DataFrame:
        """Re-runs append rows; the most recent measurement of each key wins."""
        if not schema.key_columns:
            return frame
        ordered = frame.sort_values("timestamp", kind="stable") if "timestamp" in frame.columns else frame
        return ordered.drop_duplicates(subset=list(schema.key_columns), keep="last")


# --------------------------------------------------------------------------- enrichment
class StoragePathClassifier:
    """Maps a disk_usage `path` (file path or connection string) to (layer, component).

    Handles both result layouts: '<lang>/datalake|datamarts/...' (Go/Java/Rust) and the
    Python '.../index/...' variant, plus MongoDB/PostgreSQL connection strings.
    """

    def classify(self, path: str) -> tuple[str, str]:
        normalized = str(path).strip().replace("\\", "/").lower()
        name = normalized.rstrip("/").rsplit("/", 1)[-1]
        if "/datalake/" in normalized:
            return "Datalake", name.replace("_", "-").capitalize()
        if normalized.startswith("mongodb://"):
            return self._classify_mongo_collection(normalized)
        if "dbname=" in normalized or normalized.startswith(("postgres://", "postgresql://")):
            return "Metadata", "PostgreSQL"
        if normalized.endswith((".db", ".sqlite", ".sqlite3")):
            return "Metadata", "SQLite"
        if "inverted_index" in name:
            return "Index", "JSON file" if name.endswith(".json") else "Folder"
        return "Other", name

    @staticmethod
    def _classify_mongo_collection(connection: str) -> tuple[str, str]:
        collection = connection.rsplit(".", 1)[-1]
        return ("Index" if "index" in collection else "Metadata"), "MongoDB"


def annotate_storage_layers(disk_usage: pd.DataFrame) -> pd.DataFrame:
    classifier = StoragePathClassifier()
    layers = disk_usage["path"].map(classifier.classify)
    return disk_usage.assign(storage_layer=layers.str[0], storage_component=layers.str[1],
                             test_name=layers.str[0] + ": " + layers.str[1])


def annotate_recovery_integrity(recovery: pd.DataFrame) -> pd.DataFrame:
    """A resumed run is safe when before + after == total and nothing was duplicated or lost."""
    processed = recovery["processed_before_interruption"] + recovery["processed_after_resume"]
    safe = (processed == recovery["total_books"]) & (recovery["duplicated"] == 0) & (recovery["lost"] == 0)
    return recovery.assign(integrity_ok=safe)


METRIC_ENRICHERS = {"disk_usage": annotate_storage_layers, "recovery": annotate_recovery_integrity}


def select_comparable_tests(metrics: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Charts compare languages, so tests measured by fewer than 2 languages (e.g. Python-only
    metadata inserts) are left out of every chart. They stay in the appendix CSV."""
    comparable = {metric: rows_of_multi_language_tests(frame) for metric, frame in metrics.items()}
    for metric, frame in metrics.items():
        excluded = sorted(set(frame["test_name"]) - set(comparable[metric]["test_name"]))
        if excluded:
            LOGGER.info("%s: single-language tests left out of the charts: %s", metric, ", ".join(excluded))
    return comparable


# --------------------------------------------------------------------------- loading
class BenchmarkResultsLoader:
    """Loads every language folder and merges the core metrics across languages. Any other CSV
    (e.g. go/memstats.csv) is language-specific and deliberately ignored."""

    def __init__(self, results_dir: Path) -> None:
        self.results_dir = results_dir
        self.reader = CsvTableReader()
        self.cleaner = MetricTableCleaner()

    def load(self) -> BenchmarkResults:
        language_dirs = self._language_directories()
        self._report_ignored_files(language_dirs)
        metrics = {metric: self._load_metric(metric, language_dirs) for metric in CORE_METRICS}
        metrics = {metric: METRIC_ENRICHERS.get(metric, _unchanged)(frame)
                   for metric, frame in metrics.items() if not frame.empty}
        if not metrics:
            raise FileNotFoundError(f"No usable benchmark CSVs under {self.results_dir.resolve()}")
        languages = order_languages(pd.concat([frame["language"] for frame in metrics.values()]))
        return BenchmarkResults(metrics, select_comparable_tests(metrics), tuple(languages))

    def _language_directories(self) -> list[Path]:
        if not self.results_dir.is_dir():
            raise FileNotFoundError(f"Results directory not found: {self.results_dir.resolve()}")
        directories = {directory.name.lower(): directory for directory in self.results_dir.iterdir() if directory.is_dir()}
        return [directories[language] for language in order_languages(directories)]

    def _load_metric(self, metric: str, language_dirs: Sequence[Path]) -> pd.DataFrame:
        frames = [self._load_table(directory / f"{metric}.csv", METRIC_SCHEMAS[metric]) for directory in language_dirs]
        non_empty = [frame for frame in frames if not frame.empty]
        return pd.concat(non_empty, ignore_index=True, sort=False) if non_empty else pd.DataFrame()

    @staticmethod
    def _report_ignored_files(language_dirs: Sequence[Path]) -> None:
        for path in (path for directory in language_dirs for path in sorted(directory.glob("*.csv"))):
            if path.stem not in CORE_METRICS:
                LOGGER.info("Ignoring %s/%s: language-specific, not part of the cross-language suite",
                            path.parent.name, path.name)

    def _load_table(self, path: Path, schema: MetricSchema) -> pd.DataFrame:
        if not path.is_file():
            LOGGER.warning("Missing %s: that language is simply absent from this metric", path)
            return pd.DataFrame()
        try:
            return self.cleaner.clean(self.reader.read(path), path.parent.name.lower(), path.stem, schema)
        except SchemaMismatchError as error:
            return self._report_schema_mismatch(path, error)

    @staticmethod
    def _report_schema_mismatch(path: Path, error: SchemaMismatchError) -> pd.DataFrame:
        LOGGER.warning("Skipping %s: %s", path, error)
        return pd.DataFrame()


def _unchanged(frame: pd.DataFrame) -> pd.DataFrame:
    return frame


# --------------------------------------------------------------------------- outputs
class MasterDatasetExporter:
    """Writes every core metric of every language into one wide CSV for the appendix."""

    LEADING_COLUMNS = ["language", "metric", "test_name"]

    def export(self, results: BenchmarkResults, path: Path) -> None:
        tables = [results.metrics[metric] for metric in CORE_METRICS if metric in results.metrics]
        master = pd.concat(tables, ignore_index=True, sort=False)
        master = self._restore_integer_columns(master, tables)
        master = self._sorted(master[self._column_order(master)], results.languages)
        path.parent.mkdir(parents=True, exist_ok=True)
        master.to_csv(path, index=False, date_format="%Y-%m-%dT%H:%M:%S.%f")
        LOGGER.info("Wrote %s (%d rows, %d columns)", path, len(master), len(master.columns))

    @staticmethod
    def _restore_integer_columns(master: pd.DataFrame, tables: list[pd.DataFrame]) -> pd.DataFrame:
        """Columns that are integers in every source table print as 25, not 25.0, after the merge."""
        integer = {column for table in tables for column in table.columns if pd.api.types.is_integer_dtype(table[column])}
        floating = {column for table in tables for column in table.columns if pd.api.types.is_float_dtype(table[column])}
        return master.assign(**{column: master[column].astype("Int64") for column in integer - floating})

    def _column_order(self, master: pd.DataFrame) -> list[str]:
        trailing = ["timestamp"] if "timestamp" in master.columns else []
        middle = [column for column in master.columns if column not in self.LEADING_COLUMNS + trailing]
        return self.LEADING_COLUMNS + middle + trailing

    @staticmethod
    def _sorted(master: pd.DataFrame, languages: Sequence[str]) -> pd.DataFrame:
        rank = {language: position for position, language in enumerate(languages)}
        sort_columns = ["metric", "language_rank", "test_name"] + (["batch_size"] if "batch_size" in master else [])
        ranked = master.assign(language_rank=master["language"].map(rank))
        return ranked.sort_values(sort_columns, kind="stable").drop(columns="language_rank")


def report_recovery_integrity(results: BenchmarkResults) -> None:
    recovery = results.metrics.get("recovery", pd.DataFrame())
    if recovery.empty:
        return
    for language, scenarios in recovery.groupby("language", sort=False):
        verdict = "PASS" if scenarios["integrity_ok"].all() else "FAIL"
        LOGGER.info("Recovery integrity %-6s %s (%d scenarios, %d duplicated, %d lost)", language_label(language), verdict,
                    len(scenarios), scenarios["duplicated"].sum(), scenarios["lost"].sum())


# --------------------------------------------------------------------------- orchestration
CHART_MODULES: tuple[BenchmarkChart, ...] = (
    ScalabilityCharts(), ThroughputChart(), LatencyChart(), StorageSankey(), ExecutiveRadar(),
)


class ChartSuite:
    """Renders each chart into charts/<subdirectory>; one failing chart never stops the others."""

    def __init__(self, charts: Sequence[BenchmarkChart]) -> None:
        self.charts = charts
        self.failed_charts: list[str] = []

    def render_all(self, results: BenchmarkResults, output_root: Path) -> None:
        for chart in self.charts:
            self._render_safely(chart, results, output_root / chart.subdirectory)

    def _render_safely(self, chart: BenchmarkChart, results: BenchmarkResults, output_dir: Path) -> None:
        try:
            chart.render(results, output_dir)
        except ChartDataError as error:
            LOGGER.warning("%s skipped: %s", type(chart).__name__, error)
        except Exception:  # noqa: BLE001 - report, keep rendering the remaining charts
            self._record_failure(chart)

    def _record_failure(self, chart: BenchmarkChart) -> None:
        LOGGER.exception("%s failed", type(chart).__name__)
        self.failed_charts.append(type(chart).__name__)


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the multi-language benchmark chart suite.")
    parser.add_argument("--results-dir", type=Path, default=Path("benchmarks_results"),
                        help="folder with <language>/<metric>.csv (default: benchmarks_results)")
    parser.add_argument("--output-dir", type=Path, default=Path("charts"),
                        help="root folder for the chart subfolders (default: charts)")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def configure_logging(level: int) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    LOGGER.setLevel(level)


def main(argv: Sequence[str] = ()) -> int:
    arguments = parse_arguments(list(argv) or sys.argv[1:])
    configure_logging(logging.DEBUG if arguments.verbose else logging.INFO)
    apply_matplotlib_theme()
    try:
        results = BenchmarkResultsLoader(arguments.results_dir).load()
    except FileNotFoundError as error:
        LOGGER.error("%s", error)
        return 1
    report_recovery_integrity(results)
    MasterDatasetExporter().export(results, arguments.output_dir / "consolidated_metrics.csv")
    suite = ChartSuite(CHART_MODULES)
    suite.render_all(results, arguments.output_dir)
    LOGGER.info("Done. Charts are in %s", arguments.output_dir.resolve())
    return 2 if suite.failed_charts else 0


if __name__ == "__main__":
    raise SystemExit(main())
