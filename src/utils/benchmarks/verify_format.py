#!/usr/bin/env python3
"""Validate a language benchmark snapshot against the Go reference snapshot.

Run from anywhere:

    python3 src/utils/benchmarks/verify_format.py docs/results/2026-10-02/rust
    python3 src/utils/benchmarks/verify_format.py docs/results/2026-10-02/python --format-only

Full mode checks header/column parity, labels and batch sizes against the Go
snapshot. `--format-only` (used for the Python baseline, whose label sets
differ by specification) checks only CSV formatting: CRLF endings, column
counts, timestamp and decimal rules.
"""
import csv
import io
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DIR = REPO_ROOT / "docs/results/2026-10-02/go"
FILES = ["benchmarks", "statistics", "scalability", "recovery", "throughput", "disk_usage"]
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}$")
DECIMALS = {
    ("benchmarks", "elapsed_seconds"): 6,
    ("benchmarks", "memory_mb"): 4,
    ("benchmarks", "cpu_percent"): 2,
    ("statistics", "mean_seconds"): 6,
    ("statistics", "stdev_seconds"): 6,
    ("statistics", "min_seconds"): 6,
    ("statistics", "max_seconds"): 6,
    ("scalability", "elapsed_seconds"): 6,
    ("scalability", "memory_mb"): 4,
    ("scalability", "cpu_percent"): 2,
    ("recovery", "detection_time"): 6,
    ("recovery", "processing_time"): 6,
    ("recovery", "elapsed_seconds"): 6,
    ("throughput", "elapsed_seconds"): 6,
    ("throughput", "items_per_second"): 4,
    ("disk_usage", "size_mb"): 4,
}
INTEGERS = {
    ("statistics", "iterations"),
    ("scalability", "batch_size"),
    ("throughput", "item_count"),
    ("recovery", "total_books"),
    ("recovery", "processed_before_interruption"),
    ("recovery", "processed_after_resume"),
    ("recovery", "duplicated"),
    ("recovery", "lost"),
    ("disk_usage", "file_count"),
    ("disk_usage", "dir_count"),
}
LABEL_COLUMNS = {"benchmarks": "function_name", "statistics": "test_name",
                 "scalability": "test_name", "recovery": "test_name",
                 "throughput": "test_name"}


def read_rows(path):
    raw = path.read_bytes()
    issues = []
    if b"\r\n" not in raw or raw.replace(b"\r\n", b"").count(b"\n"):
        issues.append(f"{path.name}: line endings are not uniformly CRLF")
    text = raw.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    return rows, issues


def check_format(name, header, data, issues):
    if header[-1] != "timestamp":
        issues.append(f"{name}.csv: header must end with timestamp")
    for row in data:
        if len(row) != len(header):
            issues.append(f"{name}.csv: row {row} has {len(row)} columns, expected {len(header)}")
            continue
        record = dict(zip(header, row))
        if not TIMESTAMP.match(record["timestamp"]):
            issues.append(f"{name}.csv: bad timestamp {record['timestamp']}")
        for column, digits in DECIMALS.items():
            if column[0] == name and column[1] in record:
                pattern = r"^-?\d+\.\d{" + str(digits) + r"}$"
                if not re.match(pattern, record[column[1]]):
                    issues.append(
                        f"{name}.csv: {column[1]}={record[column[1]]} needs {digits} decimals"
                    )
        for column in header:
            if (name, column) in INTEGERS and not re.match(r"^-?\d+$", record[column]):
                issues.append(f"{name}.csv: {column}={record[column]} must be an integer")


def check_parity(name, header, data, reference_header, reference_data, issues):
    if header != reference_header:
        issues.append(f"{name}.csv: header {header} != {reference_header}")
    label = LABEL_COLUMNS.get(name)
    if label:
        got = [row[header.index(label)] for row in data]
        want = [row[reference_header.index(label)] for row in reference_data]
        if got != want:
            issues.append(f"{name}.csv: labels {got} != {want}")
    if name == "scalability":
        got = [(row[0], row[1]) for row in data]
        want = [(row[0], row[1]) for row in reference_data]
        if got != want:
            issues.append("scalability.csv: (test_name, batch_size) pairs differ from reference")
    if name == "recovery":
        for row in data:
            if row[header.index("duplicated")] != "0" or row[header.index("lost")] != "0":
                issues.append(f"recovery.csv: nonzero duplicated/lost in {row}")


def check_snapshot(target_dir, format_only):
    issues = []
    for name in FILES:
        target = target_dir / f"{name}.csv"
        if not target.exists():
            issues.append(f"{name}.csv: missing")
            continue
        target_rows, row_issues = read_rows(target)
        issues.extend(row_issues)
        header, data = target_rows[0], target_rows[1:]
        check_format(name, header, data, issues)
        if format_only:
            continue
        reference_rows, _ = read_rows(REFERENCE_DIR / f"{name}.csv")
        check_parity(name, header, data, reference_rows[0], reference_rows[1:], issues)
    return issues


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target_dir = Path(sys.argv[1])
    format_only = "--format-only" in sys.argv[2:]
    found = check_snapshot(target_dir, format_only)
    for issue in found:
        print(f"ISSUE: {issue}")
    print(f"{len(found)} format issues")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
