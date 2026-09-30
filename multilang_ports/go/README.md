# Go port — Stage 1 data layer benchmark

Go implementation of the Stage 1 datalake (Section 3.1) and inverted index
(Section 4.2). It mirrors the Python baseline in `src/` rule for rule, so its
outputs can be compared 1:1 with the Python, Rust, Java and C versions.

## Layout

```
go/
├── main.go                 # CLI: build | query | bench
├── utils/                  # tokenizer/normalizer + <id>_body.txt discovery
├── datalake/               # Gutenberg fetch, START/END split, 3 hierarchies
├── datamarts/              # postings + JSON file, MongoDB and folder indexes
└── benchmark/              # timing, runtime.MemStats, CPU, disk usage, CSVs
```

## Setup

Requires Go 1.22+. Download the MongoDB driver once (this also creates `go.sum`):

```bash
cd multilang_ports/go
go mod tidy
```

MongoDB is optional: start it with `docker compose up -d` from the repository
root. Without it the MongoDB index (and its tests) are skipped, as in Python.

## Usage

```bash
# Same contract as the Rust/Java/C ports
go run . build ../../sample_data/bodies output/inverted_index.json
go run . query output/inverted_index.json alice darcy

# Full benchmark: fills the 3 layouts from the tracked corpus, then
# downloads a 10-book probe from Gutenberg (skipped when offline)
go run . bench
go run . bench -raw-dir ./raw_books          # offline: reads pg<id>.txt files
go run . bench -skip-mongo -query-repetitions 500
go run . bench -h                             # every flag

go test ./...                                 # unit tests
```

Datalake and index artifacts go to `~/.cache/stage_1_benchmarks/go`
(fast filesystem, same policy as the Python suite) and CSV results are
appended to `results/` (git-ignored). Building the folder index writes one
file per term, which takes 10+ minutes on a Windows-mounted working copy.

## Parity with the Python baseline

| Aspect | Rule (same as `src/`) |
|---|---|
| Split | text before `*** START OF THE PROJECT GUTENBERG EBOOK` is the header; text up to the next `*** END OF THE PROJECT GUTENBERG EBOOK` is the body; both `str.strip()`-ed |
| Datalake files | `<id>_body.txt`, `<id>_header.txt` in `YYYYMMDD/HH/`, `<id>/` or `batch_<lo>_<hi>/` (batch size 1000) |
| Tokenizer | `re.findall(r"[a-z]+", text.lower())`, then drop stop words, Roman numerals and 1-letter tokens |
| JSON index | byte-identical to `json.dump(index, f, ensure_ascii=False, indent=2)`, terms in first-appearance order |
| Folder index | `<LETTER>/<term>.txt`, one book ID per line |
| MongoDB | `search_engine.inverted_index`, `{"term", "postings"}` documents, unique index on `term`, delete-all + `insert_many` |
| Execution | strictly sequential, like the Python version |

## Metrics

Files mirror `src/utils/benchmarks/storage.py` (same columns, number formats
and CRLF line endings), so they can be merged with the Python results:

- `benchmarks.csv` — elapsed seconds, memory MB, CPU % per operation.
  `memory_mb` is the growth of `runtime.MemStats.Sys` (memory obtained from
  the OS), the closest analogue of the RSS delta psutil gives Python.
- `memstats.csv` — Go-only detail: heap delta, total allocated, heap in use, GC cycles.
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
`-bodies`/`-headers`) and queries come from the shared workload file (`src/utils/benchmarks/queries.txt`,
intersection semantics); the default `-query-repetitions 5` yields 100
samples per query test, like Python.

A published snapshot of this suite lives in
`docs/results/2026-09-30/go/`, next to the Python snapshot it is compared
against. The metadata rows (`insert_*`, `query_*_sqlite`,
`insert_throughput_*`) are Python-only by specification.
