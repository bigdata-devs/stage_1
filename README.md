# Boogle Engine — Stage 1: Building the Data Layer

Big Data course project (Grado en Ciencia e Ingeniería de Datos, ULPGC).
Stage 1 builds the data layer of a book search engine over Project Gutenberg:

- a **datalake** with the raw header and body of every downloaded book,
- **datamarts** with the book metadata (SQLite) and the inverted index
  (monolithic JSON file, hierarchical folder of term files, MongoDB),
- a **control layer** that coordinates downloading and indexing without
  duplicating or losing books,
- a **benchmark suite** that compares datalake layouts and inverted-index
  structures in four languages: Python (baseline), Go, Rust and Java.

Group: `bigdata-devs` — repository: <https://github.com/bigdata-devs/stage_1>

## Repository structure

```
stage_1/
├── main.py                     # entry point: runs the control-layer pipeline
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # optional MongoDB 7 server
├── src/
│   ├── control/                # control layer: state files, controller, pipeline tasks
│   ├── datalake/               # Gutenberg download + header/body split, 3 layouts
│   ├── datamarts/
│   │   ├── metadata/           # header parser + SQLite/PostgreSQL/MongoDB storage
│   │   └── inverted_index/     # JSON, folder and MongoDB index structures
│   └── utils/
│       ├── text_processor.py   # shared tokenizer/normalizer rules
│       └── benchmarks/         # Python benchmark suite + shared queries.txt
├── tests/                      # pytest suite for the Python code
├── data_source/                # frozen 100-book benchmark corpus (bodies/, headers/, manifest.json)
├── sample_data/                # 4-book sample dataset for quick checks
├── multilang_ports/
│   ├── go/                     # Go port (datalake, datamarts, benchmark)
│   ├── rust/                   # Rust port
│   └── java/                   # Java port
├── docs/results/<date>/<lang>/ # published benchmark CSV snapshots
├── prototypes/c_port/          # archived C prototype (not built or benchmarked)
├── datalake/                   # generated: pipeline datalake (git-ignored)
├── datamarts/                  # generated: metadata.db, inverted_index.json (git-ignored)
└── control/                    # generated: control files (git-ignored)
```

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

docker compose up -d               # optional: MongoDB for the MongoDB index
```

Without MongoDB the pipeline still works; the MongoDB experiments and tests
are skipped.

## 1. Python pipeline: populating the Datalake and Datamarts

The control layer runs the pipeline step by step. At each step it either
indexes one downloaded book that is still pending or, if none is pending,
downloads a new random book ID that was never tried before.

```bash
python main.py --steps 20          # same as: python -m src.control --steps 20
```

What each step writes (all paths relative to the repository root):

| Stage | Output |
|---|---|
| Download | `datalake/YYYYMMDD/HH/<BOOK_ID>_header.txt` and `<BOOK_ID>_body.txt` (time-based layout, atomic writes) |
| Metadata | row in `datamarts/metadata.db` (SQLite table `books`: `book_id`, `title`, `author`, `language`, `capture_date`, `header_path`, `body_path`) |
| Inverted index | postings merged into `datamarts/inverted_index.json` |
| State | `control/downloaded_books.txt`, `control/indexed_books.txt`, `control/failed_books.txt` |

The control files make the pipeline resumable: stopping it and running
`main.py` again continues where it left off, without downloading or indexing
a book twice. IDs that do not exist on Gutenberg (or lack the START/END
markers) go to `failed_books.txt` and are never requested again.

Rebuilding the datamarts from what is already in the datalake:

```bash
python -m src.datamarts.metadata.book_processor             # metadata.db from every header
python -m src.datamarts.inverted_index.build_inverted_index # datamarts/inverted_index.json
python -m src.datamarts.inverted_index.build_folder_index   # datamarts/inverted_index/<LETTER>/<term>.txt
python -m src.datamarts.inverted_index.build_mongo_index    # MongoDB search_engine.inverted_index
```

The index builders take the list of books and their body paths from
`metadata.db`, so run `book_processor` (or the pipeline) first.

## 2. Benchmarks

### Shared inputs

Every language benchmarks exactly the same workload, so differences come from
the language and the storage structure, not from the data:

- **Corpus:** `data_source/bodies/<id>_body.txt` and
  `data_source/headers/<id>_header.txt` — 100 Gutenberg books frozen in git
  (the IDs are listed in `data_source/manifest.json`). No port downloads its
  own corpus; the only network access is an identical 10-book download probe
  that measures download throughput and is skipped when offline.
- **Queries:** `src/utils/benchmarks/queries.txt` — 20 queries, one per line;
  a query matches the books that contain every term (postings intersection).
- **Rules:** the same header/body split, tokenizer (`[a-z]+`, stop words,
  Roman numerals, 1-letter tokens), layouts and index formats. The four ports
  build byte-identical `inverted_index.json` files from the corpus.

Each language writes its generated datalakes and indexes to
`~/.cache/stage_1_benchmarks/[<lang>/]`, the Python metadata benchmark uses
`~/.cache/stage_1_benchmarks/metadata/metadata_benchmark.db`, and every MongoDB
experiment runs in the `search_engine_benchmark` database, so benchmarks never
touch the pipeline's `datalake/`, `datamarts/metadata.db` or the
`search_engine` MongoDB datamart.

### What is measured

- **Datalake** (time-based, book-based and batch-based layouts): write
  throughput, lookup latency, incremental detection of new books, resume
  after an interrupted run, and storage overhead (size, files, folders).
- **Inverted index** (JSON file, folder of term files, MongoDB): build time
  for 10–500 books, latency of the shared queries, adding one book to an
  existing index, and storage size.
- **Metadata** (Python only, optional in the guide): insert throughput and
  queries on SQLite, PostgreSQL (needs `psycopg2` and a local server,
  otherwise skipped) and MongoDB.

### Running each language

```bash
# Python (baseline) — CSVs in src/utils/benchmarks/results/
python -m src.utils.benchmarks.benchmark_implementations

# Go — CSVs in multilang_ports/go/results/
cd multilang_ports/go && go run . bench

# Rust — CSVs in multilang_ports/rust/results/
cd multilang_ports/rust && cargo run --release --bin bench -- bench

# Java — CSVs in multilang_ports/java/results/
cd multilang_ports/java && mvn -q compile exec:java -Dexec.mainClass=benchmark.Main -Dexec.args="bench"
```

Useful flags for the Go/Rust/Java runners: `-skip-mongo`,
`-query-repetitions N`, `-raw-dir <folder>` (offline download probe from
`pg<id>.txt` files). See each port's `README.md` for details.

All runners write the same CSV files (`benchmarks`, `throughput`,
`statistics`, `scalability`, `recovery`, `disk_usage`) with the same columns.
Check a snapshot against the reference format with:

```bash
python src/utils/benchmarks/verify_format.py docs/results/<date>/rust
```

The Rust and Java runners read memory (and Rust also CPU time) from
`/proc`, so run the final benchmarks on Linux.

## Tests

```bash
python -m pytest                             # Python
cd multilang_ports/go && go test ./...       # Go
cd multilang_ports/rust && cargo test        # Rust
cd multilang_ports/java && mvn test          # Java
```

MongoDB tests are skipped when no server is reachable.

## Sample dataset

`sample_data/` holds 4 books (IDs 11, 84, 174, 1342) for quick checks, for
example:

```bash
cd multilang_ports/go && go run . build ../../sample_data/bodies output/inverted_index.json
```

Regenerate it with `python -m src.datalake.download_sample_data`. The
100-book benchmark corpus in `data_source/` doubles as a larger test dataset.
