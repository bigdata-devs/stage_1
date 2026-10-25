# Reproducing the Benchmark Results

This document describes how to reproduce every number that appears in the
report: the cross-language comparison, the JMH micro-benchmarks, the charts
and the environment record. The whole tournament is one command; each phase
can also be run alone.

## Prerequisites

| Tool | Used for | Notes |
| --- | --- | --- |
| Python 3.11+ | baseline suite, checker, charts | `pip install -r requirements.txt` |
| Go 1.22+ | Go port | `go build ./...` must succeed |
| Rust (stable) + Cargo | Rust port | `cargo build --release` must succeed |
| Java 21 + Maven | Java port and JMH | `mvn -q compile` must succeed; the harness needs a heap that fits the largest batch (the tournament defaults `MAVEN_OPTS` to `-Xmx5g`) |
| MongoDB (optional) | mongo index structure | every port skips it consistently when unreachable |

The exact versions of the run that produced the committed snapshot are
recorded in `benchmarks_results/environment.txt`. Run the toolchains from the
repository root so the default relative paths (`data_source/bodies`,
`src/utils/benchmarks/queries.txt`) resolve.

## The dataset

`data_source/` carries the sample corpus (`headers/` and `bodies/`, one pair
of files per Gutenberg book id). Every language reads exactly these files, so
no download step is needed to reproduce the benchmark.

## One command

```bash
scripts/run_tournament.sh
```

The script runs the phases in this order and aborts on the first failure:

0. **Equivalence** — each port writes the canonical file (per-book token
   streams, postings lists, query results) for the same 100-book sample; the
   checker compares the four files byte for byte and writes
   `benchmarks_results/equivalence_report.json`. Timings are meaningless
   without this check, so it always runs first.
1. **Benchmarks** — Go, Rust and Java write their CSVs directly into
   `benchmarks_results/<language>/`; the Python baseline writes to
   `src/utils/benchmarks/results/` and is copied afterwards. Java additionally
   runs the JMH suite (`multilang_ports/java/run_jmh.sh`), which refreshes
   `benchmarks_results/java/jmh_results.json`.
2. **Verify** — `verify_format.py` checks CRLF endings, columns, decimals and
   timestamps for every snapshot (`--format-only` for Python and Go, full row
   parity against the Go reference for Rust and Java).
3. **Environment** — `benchmarks_results/environment.txt` records kernel, CPU,
   memory, dataset size and toolchain versions of the run.
4. **Charts** — `python3 -m src.visualizations.main --output-dir charts`
   renders the shared chart suite from the fresh snapshot.

Logs land in `$BENCH_LOG_DIR` (default
`~/.cache/stage_1_benchmarks/bench_logs/`).

## Measurement protocol (identical for every language)

- **Warm-up**: only the Java harness warms up (one unmeasured build per
  structure) because only the JVM has a JIT; Go, Rust and Python start timing
  immediately. The JMH micro-benchmarks use the standard JMH protocol
  (5 warm-up iterations, 5 measurement iterations, 1 fork, GC profiler) and
  are **Java-only evidence**: they must never be mixed with harness rows.
- **Repetitions**: scalability builds repeat 5 times up to 1000 books, 3 times
  up to 5000 and 2 times above; isolated updates always repeat 5 times. Rows
  report mean, sample deviation and peak.
- **Memory**: resident-set-size delta plus a peak sampler (every 50 ms);
  the peak is the maximum over repetitions.
- **CPU**: process CPU time divided by wall clock, so a slow disk shows up
  as low CPU instead of inflating the figure.
- **Disk/cache**: the phases run sequentially on the same working set; caches
  are not dropped (no root required) and every language faces the same cache
  state because each one starts after the previous finished.
- **Recovery**: every port simulates an interruption by processing the first
  half of the corpus, detecting the pending books and resuming; the rows must
  report zero duplicated and zero lost books.
- **Updates**: each structure receives five single-book additions on top of an
  untimed base index of 25, 50, 250, 500 and 1000 books (`updates.csv`), so
  the scaling of the update cost is measured instead of claimed.

## Running one phase alone

```bash
# Phase 0: equivalence only
python3 -m src.utils.benchmarks.equivalence_check

# Phase 1: one language (same commands the script uses)
(cd multilang_ports/go && go run . bench -results ../../benchmarks_results/go)
(cd multilang_ports/rust && cargo run --release --bin bench -- bench -results ../../benchmarks_results/rust)
(cd multilang_ports/java && mvn -q compile exec:java "-Dexec.mainClass=benchmark.Main" "-Dexec.args=bench -results ../../benchmarks_results/java")
python3 -m src.utils.benchmarks.benchmark_implementations   # copies itself: see the script
cp src/utils/benchmarks/results/*.csv benchmarks_results/python/

# JMH micro-benchmarks (Java protocol only)
./multilang_ports/java/run_jmh.sh

# Phase 2: verification
python3 src/utils/benchmarks/verify_format.py benchmarks_results/go --format-only
python3 src/utils/benchmarks/verify_format.py benchmarks_results/python --format-only
python3 src/utils/benchmarks/verify_format.py benchmarks_results/rust
python3 src/utils/benchmarks/verify_format.py benchmarks_results/java

# Phase 4: charts
python3 -m src.visualizations.main --output-dir charts
```

## Interpreting the snapshot

- `benchmarks_results/<language>/*.csv` — the committed snapshot each report
  figure is built from; regenerate it only with the tournament so format and
  parity stay intact.
- `benchmarks_results/equivalence_report.json` — digests proving the four
  languages processed identical tokens, postings and query results.
- `benchmarks_results/java/jmh_results.json` — Java micro-evidence (JMH
  protocol), separate from the cross-language rows on purpose.
- `charts/` — rendered figures; `charts/consolidated_metrics.csv` holds the
  cleaned master table behind them.
