"""Metadata insert rows must follow the extended scalability schema
(stdev_seconds, repetitions, peak_rss_mb) that save_scalability requires."""

import csv
import io
from dataclasses import dataclass

import src.utils.benchmarks.metadata_experiments as metadata_experiments
from src.utils.benchmarks import storage
from src.utils.benchmarks.verify_format import check_format, read_rows

SCALABILITY_HEADER = [
    "test_name", "batch_size", "elapsed_seconds", "stdev_seconds", "repetitions",
    "memory_mb", "cpu_percent", "peak_rss_mb", "timestamp",
]


@dataclass
class FakeMetadataRow:
    book_id: int
    title: str = "A title"


class RecordingStorage:
    def __init__(self):
        self.saved_batch_sizes = []

    def save_many(self, rows):
        self.saved_batch_sizes.append(len(rows))


def run_insert_scalability(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(metadata_experiments, "SCALABILITY_BATCH_SIZES", [3, 7])
    recorded = RecordingStorage()
    metadata_experiments.measure_insert_scalability(recorded, FakeMetadataRow(1), "sqlite")
    return recorded


def test_measure_insert_scalability_writes_the_canonical_schema(tmp_path, monkeypatch):
    recorded = run_insert_scalability(tmp_path, monkeypatch)

    rows, issues = read_rows(tmp_path / "scalability.csv")

    assert recorded.saved_batch_sizes == [3, 7]
    assert issues == []
    assert rows[0] == SCALABILITY_HEADER
    format_issues = []
    check_format("scalability", rows[0], rows[1:], format_issues)
    assert format_issues == []


def test_single_sample_rows_record_zero_stdev_and_one_repetition(tmp_path, monkeypatch):
    run_insert_scalability(tmp_path, monkeypatch)

    raw_csv = (tmp_path / "scalability.csv").read_text(encoding="utf-8")
    data_rows = list(csv.reader(io.StringIO(raw_csv, newline="")))[1:]

    assert [row[3] for row in data_rows] == ["0.000000", "0.000000"]
    assert [row[4] for row in data_rows] == ["1", "1"]
