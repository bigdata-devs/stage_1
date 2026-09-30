# Rust port — Stage 1 data layer benchmark

Rust implementation of the Stage 1 datalake (Section 3.1) and inverted index
(Section 4.2). It mirrors the Python baseline in `src/` rule for rule, so its
outputs can be compared 1:1 with the Python, Go and Java versions.

## Layout

```
rust/
├── Cargo.toml               # library + procesador/datalake/index/bench CLIs
├── lib.rs                   # shared crate: datalake, inverted_index, datamarts, benchmark
├── datalake/                # Gutenberg fetch, START/END split, 3 hierarchies
├── inverted_index/          # tokenizer, corpus, postings, JSON index, CLI
├── datamarts/               # folder index and MongoDB index
├── metadata/                # procesador bin: SQLite/Postgres/Mongo metadata layer
└── benchmark/               # timing, VmRSS, CPU, disk usage, CSV writers, suite
```

## Setup

Requires a stable Rust toolchain (`cargo`). MongoDB is optional: start it with
`docker compose up -d` from the repository root. Without it the MongoDB index
(and its tests) is skipped, as in Python.

## Usage

```bash
cd multilang_ports/rust

# Same contract as the Python/Go/Java ports
cargo run --bin index -- build ../../data_source/bodies output/inverted_index.json
cargo run --bin index -- query output/inverted_index.json alice darcy

# Full benchmark: fills the 3 layouts from the tracked corpus, then
# downloads a 10-book probe from Gutenberg (skipped when offline)
cargo run --release --bin bench -- bench
cargo run --release --bin bench -- bench -raw-dir ./raw_books   # offline: reads pg<id>.txt
cargo run --release --bin bench -- bench -skip-mongo -query-repetitions 500

cargo test                                    # unit tests (55)
```

Datalake and index artifacts go to `~/.cache/stage_1_benchmarks/rust`
(fast filesystem, same policy as the Python suite) and CSV results are
appended to `results/` (git-ignored).

## Parity with the Python baseline

| Aspect | Rule (same as `src/`) |
|---|---|
| Split | text before `*** START OF THE PROJECT GUTENBERG EBOOK` is the header; text up to the next `*** END OF THE PROJECT GUTENBERG EBOOK` is the body; both stripped |
| Datalake files | `<id>_body.txt`, `<id>_header.txt` in `YYYYMMDD/HH/`, `<id>/` or `batch_<lo>_<hi>/` (batch size 1000) |
| Tokenizer | `[a-z]+` tokens of the lowercased text, then drop stop words, Roman numerals and 1-letter tokens |
| JSON index | terms in first-appearance order, one entry per term |
| Folder index | `<LETTER>/<term>.txt`, one book ID per line |
| MongoDB | `search_engine.inverted_index`, `{"term", "postings"}` documents, unique index on `term`, unordered bulk upserts |
| Execution | strictly sequential, like the Python version |

## Metrics

Files mirror `src/utils/benchmarks/storage.py` (same columns, number formats
and CRLF line endings), so they can be merged with the Python results:

- `benchmarks.csv` — elapsed seconds, memory MB, CPU % per operation.
  `memory_mb` is the delta of the `VmRSS` field of `/proc/self/status`, the
  same resident-set measure psutil gives Python (Linux only).
- `throughput.csv` — books per second for the download probe, each datalake
  layout write and the tokenization.
- `disk_usage.csv` — size, files and directories of every output (MongoDB:
  collection storage size, zero files/dirs, like Python).
- `statistics.csv` — latency (mean/stdev/min/max) of the shared query
  workload and of the datalake lookups.
- `scalability.csv` — per-structure build time of 10/25/50/100/250/500
  books (real corpus topped up with synthetic books), as in Python.
- `recovery.csv` — interrupted-run resume per layout: detection time,
  processing time, duplicated and lost books.

Measured operations: `write_throughput_<layout>`, `incremental_<layout>`,
`download_write_throughput`, `tokenize_books`, `build_postings`,
`load_json_index`, `update_<json|folder|mongo>_index`, plus the
`lookup_<layout>` / `query_<structure>` statistics rows, the
`build_<structure>` scalability rows and the `recovery_<layout>` rows —
the same labels as the Python suite wherever both produce a row.

Defaults: books and headers come from the tracked 100-book corpus
(`data_source/bodies` and `data_source/headers`, overridable with
`-bodies`/`-headers`) and queries come from the shared workload file
(`src/utils/benchmarks/queries.txt`, intersection semantics); the default
`-query-repetitions 5` yields 100 samples per query test, like Python.

A published snapshot of this suite lives in
`docs/results/2026-09-30/rust/`, next to the Python and Go snapshots it is
compared against. The metadata rows (`insert_*`, `query_*_sqlite`,
`insert_throughput_*`) are Python-only by specification.
