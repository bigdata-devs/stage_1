# Boogle Engine
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Java](https://img.shields.io/badge/java-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)
![Go](https://img.shields.io/badge/go-%2300ADD8.svg?style=for-the-badge&logo=go&logoColor=white)
![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)

## Overview

**Boogle Engine** is the course project for *Big Data* and its goal is a
search engine for thousands to millions of public-domain books from
[Project Gutenberg](https://www.gutenberg.org/), built in three layers:

- **Datalake**: the raw header and body of every downloaded book, kept unstructured.
- **Datamarts**: structured, queryable data. Book metadata goes in SQLite and the inverted
  index maps each term to the books that contain it.
- **Control layer**: decides at every step whether to download a new book or index a pending
  one. It never duplicates or loses work, and it can resume after an interruption.

### Reference pipeline for Stage 1, target stack for Stage 2

This repository contains **two kinds of code with two different jobs**:

| | **Stage 1 Reference Pipeline** | **Benchmark PoC ports** |
|---|---|---|
| **Purpose** | The complete, working Stage 1 system you run and evaluate | Isolated proofs of concept that measure performance and justify the Stage 2 stack |
| **Language** | Python 3.10+ | Go, Rust and Java (with Python as the baseline) |
| **Scope** | Control layer + datalake + datamarts, end to end | Datalake layouts, tokenizer and inverted-index structures only. No control layer. |
| **Data** | Live downloads from Project Gutenberg | A frozen 100-book corpus and 30 shared queries, identical for every language |
| **Code** | [`main.py`](main.py), [`src/`](src/) | [`multilang_ports/`](multilang_ports/) |

The benchmarks compared **3 datalake layouts × 3 inverted-index structures × 4 languages**.
Their conclusion sets the stack for **Stage 2**.

## Quick Start

This runs the **Stage 1 Reference Pipeline** end to end: download four books, store them in the
datalake and index them in the datamarts.

**You need:** Python 3.10+, Git and internet access, because books are downloaded live from
gutenberg.org. MongoDB and Docker are **not** required. Full requirements are listed in
[Prerequisites](#prerequisites).

```bash
# 1. Clone the repository
git clone https://github.com/bigdata-devs/stage_1.git
cd stage_1

# 2. Create and activate a virtual environment (Windows: see the PowerShell block below)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install the dependencies
pip install -r requirements.txt

# 4. Run 8 pipeline steps: each book takes 2 steps (download, then index), so this ingests 4 books
python main.py --steps 8
```

<details>
<summary><b>Windows (PowerShell)</b>: step 2</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If script execution is blocked, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

Steps 1, 3 and 4 are the same on every platform.

</details>

## Prerequisites

The Quick Start only needs **Python and Git**. The other tools are for the benchmark ports and
the MongoDB experiments.

| Tool | Version | Needed for | Verify |
|---|---|---|---|
| Python | 3.10+ | Reference pipeline, Python benchmark, tests, charts | `python --version` |
| Git | any recent | Cloning the repository | `git --version` |
| Docker + Compose v2 | any recent | MongoDB 7 for the benchmarks (optional) | `docker --version` and `docker compose version` |
| Go | 1.22+ | Go benchmark port | `go version` |
| Rust | stable, via [rustup](https://rustup.rs/) | Rust benchmark port | `cargo --version` |
| JDK | 21 | Java benchmark port | `java --version` |
| Maven | 3.x | Building and running the Java port | `mvn --version` |

## Installation & Configuration

The Python environment was set up in the [Quick Start](#quick-start) (steps 1–3). The steps
below are only needed for the benchmarks and charts. They are bash commands, run from the
repository root on Linux or WSL2.

**1. Extra Python packages for the charts and their tests** (not in `requirements.txt`):

```bash
pip install pandas numpy matplotlib plotly
```

**2. Benchmark port dependencies:**

```bash
(cd multilang_ports/go   && go mod download)
(cd multilang_ports/rust && cargo build --release)
(cd multilang_ports/java && mvn -q compile)
```

**3. MongoDB:**

```bash
docker compose up -d                # starts mongo:7 as container "stage1-mongodb" on port 27017
docker compose ps                   # wait until STATUS shows "(healthy)"
docker exec stage1-mongodb mongosh --quiet --eval "db.adminCommand('ping')"   # expected: { ok: 1 }
```

Benchmark collections are not reset between runs. Drop the benchmark database before a final
run so the results measure fresh inserts:

```bash
docker exec stage1-mongodb mongosh search_engine_benchmark --quiet --eval "db.dropDatabase()"
```

`docker compose down` stops MongoDB, and `docker compose down -v` also deletes its data. If you
have no Docker, pass `-skip-mongo` to the ports. The Python benchmark and the tests skip the
MongoDB experiments automatically when no server is reachable.

## Running the Benchmarks

Every port processes the same workload: the frozen corpus in `data_source/` (100 books, IDs in
`data_source/manifest.json`), the 30 queries in `src/utils/benchmarks/queries.txt`, and the
same tokenizer and index formats. The only network access is a 10-book download probe, which
is skipped when offline.

Run from the repository root on Linux or WSL2, with MongoDB running (or add `-skip-mongo`):

```bash
# Go
(cd multilang_ports/go && go run . bench -results ../../benchmarks_results/go)

# Rust
(cd multilang_ports/rust && cargo run --release --bin bench -- bench -results ../../benchmarks_results/rust)

# Java
(cd multilang_ports/java && mvn -q compile exec:java "-Dexec.mainClass=benchmark.Main" "-Dexec.args=bench -results ../../benchmarks_results/java")

# Python baseline: it always writes to src/utils/benchmarks/results/, so copy the CSVs afterwards
python -m src.utils.benchmarks.benchmark_implementations
cp src/utils/benchmarks/results/*.csv benchmarks_results/python/
```

Each runner writes the same six CSVs (`benchmarks`, `throughput`, `statistics`, `scalability`,
`recovery`, `disk_usage`) with identical columns.

### Generate the charts

```bash
python -m src.visualizations.main   # reads benchmarks_results/, writes charts/
```

This produces scalability, throughput, latency, storage (Sankey) and radar charts as SVG, PDF
and PNG (HTML for the interactive ones), plus `charts/consolidated_metrics.csv`.

## Testing

The test suites need no internet access. Tests that require MongoDB are skipped when no
server is reachable.

```bash
# Python, core suite (works with requirements.txt only)
python -m pytest --ignore=tests/test_visualizations

# Python, full suite (needs the chart packages from Installation step 1)
python -m pytest

# Benchmark ports
(cd multilang_ports/go   && go test ./...)
(cd multilang_ports/rust && cargo test)
(cd multilang_ports/java && mvn -q test)
```

## Roadmap (Stage 2)

Stage 2 moves the system onto the stack selected by the Stage 1 benchmarks and adds the
crawling, indexing and querying modules:

- **Go** replaces Python as the main language, with concurrent downloaders and indexers.
  In the published run, Go built the JSON index for 10,000 books in 77 s, against 252 s for Rust and 1,181 s for Java.
- **Batch-based datalake** (`datalake/batch_<LOW>_<HIGH>/`) replaces the time-based layout.
- **MongoDB** stores the inverted index as one document per term, replacing the monolithic JSON
  file.

## Team

**Group `bigdata-devs`**

| Member | GitHub |
|---|---|
| Tomás Santana Suárez | [@TemiArtemi](https://github.com/TemiArtemi) |
| Carlos Montesdeoca Vega | [@CarlosMontesdeoca21](https://github.com/CarlosMontesdeoca21) |
| Aythami Lorenzo Padilla | [@aythamilorenzo](https://github.com/aythamilorenzo) |
| Javier Ruano Hernández  | [@javierruanohdez](https://github.com/javierruanohdez) |
| Alejandro Delgado Valera | [@aledelgadoo](https://github.com/aledelgadoo) |