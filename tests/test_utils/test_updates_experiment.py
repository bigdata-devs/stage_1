from pathlib import Path

import src.utils.benchmarks.storage as storage
from src.utils.benchmarks.verify_format import check_snapshot, required_files


def test_required_files_includes_updates_only_with_the_reference(tmp_path: Path, monkeypatch):
    reference = tmp_path / "go"
    reference.mkdir()
    monkeypatch.setattr("src.utils.benchmarks.verify_format.REFERENCE_DIR", reference)

    assert "updates" not in required_files()

    (reference / "updates.csv").write_bytes(b"a\r\n")
    assert "updates" in required_files()


def test_save_updates_writes_the_canonical_schema(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(storage, "RESULTS_DIR", tmp_path)

    storage.save_updates({
        "test_name": "update_json_index",
        "base_size": 250,
        "elapsed_seconds": 0.1234567,
        "stdev_seconds": 0.001234,
        "repetitions": 5,
        "memory_mb": 1.23456,
        "cpu_percent": 50.0,
        "peak_rss_mb": 2.5,
    })

    rows = (tmp_path / "updates.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0].split(",") == [
        "test_name", "base_size", "elapsed_seconds", "stdev_seconds", "repetitions",
        "memory_mb", "cpu_percent", "peak_rss_mb", "timestamp",
    ]
    assert rows[1].split(",")[:8] == [
        "update_json_index", "250", "0.123457", "0.001234", "5", "1.2346", "50.00", "2.5000",
    ]
