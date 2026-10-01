"""Benchmark artifact locations, kept apart from the pipeline's datalake and datamarts."""

from pathlib import Path

ARTIFACT_ROOT = Path.home() / ".cache" / "stage_1_benchmarks"
METADATA_BENCHMARK_DB_PATH = ARTIFACT_ROOT / "metadata" / "metadata_benchmark.db"
BENCHMARK_MONGO_DATABASE = "search_engine_benchmark"
