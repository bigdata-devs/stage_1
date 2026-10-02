# Java port — Stage 1 data layer benchmark

Java implementation of the Stage 1 datalake (Section 3.1) and inverted index
(Section 4.2). It mirrors the Python baseline in `src/` rule for rule, so its
outputs can be compared 1:1 with the Python, Go and Rust versions.

## Layout

```
java/
├── pom.xml                 # JUnit 5 tests + exec plugin for the CLIs
├── datalake/               # Gutenberg fetch, START/END split, 3 hierarchies
├── inverted_index/          # tokenizer, corpus, postings, JSON index, CLI
├── datamarts/              # folder index and MongoDB index
├── benchmark/              # timing, VmRSS, CPU, disk usage, CSV writers
└── src/test/java/          # JUnit 5 tests mirroring the Go suite
```

## Setup

Requires JDK 21+ and Maven 3.9+. MongoDB is optional: start it with
`docker compose up -d` from the repository root. Without it the MongoDB index
(and its tests) are skipped, as in Python.

## Usage

```bash
cd multilang_ports/java

# Same contract as the Rust/Go ports
mvn -q compile exec:java -Dexec.mainClass=inverted_index.Main \
    -Dexec.args="build ../../sample_data/bodies output/inverted_index.json"
mvn -q compile exec:java -Dexec.mainClass=inverted_index.Main \
    -Dexec.args="query output/inverted_index.json alice darcy"

# Full benchmark: fills the 3 layouts from the tracked corpus, then
# downloads a 10-book probe from Gutenberg (skipped when offline)
mvn -q compile exec:java -Dexec.mainClass=benchmark.Main -Dexec.args="bench"
mvn -q compile exec:java -Dexec.mainClass=benchmark.Main \
    -Dexec.args="bench -raw-dir ./raw_books"   # offline: reads pg<id>.txt
mvn -q compile exec:java -Dexec.mainClass=benchmark.Main \
    -Dexec.args="bench -skip-mongo -query-repetitions 500"

mvn test                                       # unit tests (51)
```

Datalake and index artifacts go to `~/.cache/stage_1_benchmarks/java`
(fast filesystem, same policy as the Python suite) and CSV results are
appended to `results/` (git-ignored).

## Parity with the Python baseline

| Aspect | Rule (same as `src/`) |
|---|---|
| Split | text before `*** START OF THE PROJECT GUTENBERG EBOOK` is the header; text up to the next `*** END OF THE PROJECT GUTENBERG EBOOK` is the body; both stripped |
| Datalake files | `<id>_body.txt`, `<id>_header.txt` in `YYYYMMDD/HH/`, `<id>/` or `batch_<lo>_<hi>/` (batch size 1000) |
| Tokenizer | `[a-z]+` tokens of the lowercased text, then drop stop words, Roman numerals and 1-letter tokens |
| JSON index | terms in first-appearance order, one entry per term |
| Folder index | `<LETTER>/<term>.txt`, one book ID per line; Windows device names (`con`, `aux`, `nul`, `prn`, `com1`-`com9`, `lpt1`-`lpt9`) get a trailing underscore (`C/con_.txt`) |
| MongoDB | `search_engine_benchmark.inverted_index` (`-mongo-db` overrides the database), `{"term", "postings"}` documents, unique index on `term`, unordered bulk upserts |
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
`-query-repetitions 5` yields 150 samples per query test, like Python.

A published snapshot of this suite lives in
`docs/results/2026-09-30/java/`, next to the Python and Go snapshots it is
compared against. The metadata rows (`insert_*`, `query_*_sqlite`,
`insert_throughput_*`) are Python-only by specification.
