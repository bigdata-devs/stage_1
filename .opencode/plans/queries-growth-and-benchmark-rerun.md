# Plan: query workload 30 + build batches to 10000 + re-run benchmarks

Decisions (user, 2026-10-02):
- Grow `queries.txt` 20 → 30 queries (add ~10 mid-frequency terms; bands 5-9/10-19/20-29/30-45, target intersection 2-15 books).
- Growth build batch sizes: start at 25 (drop 10), add 1000, 5000, 10000 → final set **{25, 50, 100, 250, 500, 1000, 5000, 10000}** (100 = corpus, auto-merged) in all 4 languages.
- Accept teammate's `0799387` (runtime CSVs stay un-tracked; only dated `docs/results/` snapshots tracked).
- Re-run all 4 benchmarks and publish `docs/results/2026-10-02/` (2026-09-30 stays historical). Expected ~2 h total.

## Steps

1. **Sync + baseline gates** (validate teammate's refactor `c00318f..d80d90b`):
   - `git fetch origin` + `git merge --ff-only origin/develop` on `feature/benchmarking-suite`.
   - Run pytest, `mvn test`, `cargo test`, `go test -count=1`.
     Env: `source /tmp/opencode/toolchains/rust_env.sh`, `source /tmp/opencode/toolchains/env.sh`, `export PATH=/tmp/opencode/go/bin:$PATH GOPATH=/tmp/opencode/gopath GOCACHE=/tmp/opencode/gocache`.
   - Start mongod detached (prior session command) before benchmarks.

2. **Queries 20 → 30** in `src/utils/benchmarks/queries.txt`:
   - Keep existing 20 lines; add 10 mid-DF queries (2×df 5-9, 3×df 10-19, 3×df 20-29, 2×df 30-45; 2-3 terms; intersection 2-15 books). Verify df/intersection of each candidate at execution. Match file's format (loader skips `#`/blanks).

3. **Query ripple**:
   - `multilang_ports/go/benchmark/queries_test.go:45`: `!= 20` → `!= 30` + message.
   - `README.md:109`: "20 queries" → "30 queries".
   - `multilang_ports/{go,java,rust}/README.md`: "yields 100 samples" → "yields 150 samples".
   - Grep `20 queries|100 samples` for stragglers.

4. **Build batch sizes to 10000** (4 constants + 3 test files):
   - `src/utils/benchmarks/inverted_index_experiments.py:28`: `BUILD_BATCH_SIZES = (25, 50, 250, 500, 1000, 5000, 10000)`.
   - `multilang_ports/go/benchmark/index_bench.go:153`: `sizes := []int{25, 50, 250, 500, 1000, 5000, 10000, bookCount}`.
   - `multilang_ports/go/benchmark/scalability_test.go:11,14`: expected lists (e.g. `buildBatchSizes(100)` → `{25,50,100,250,500,1000,5000,10000}`; `(250)` → `{25,50,250,500,1000,5000,10000}`).
   - `multilang_ports/rust/benchmark/index_bench.rs:17`: `const BASE_BATCH_SIZES: [usize; 7] = [25, 50, 250, 500, 1000, 5000, 10000];`.
   - `multilang_ports/rust/benchmark/index_bench.rs:367-369`: 3 `assert_eq!` (60 → `{25,50,60,250,500,1000,5000,10000}`; 10 → `{10,25,50,250,500,1000,5000,10000}`; 600 → `{25,50,250,500,600,1000,5000,10000}`).
   - `multilang_ports/java/benchmark/IndexBenchmark.java` (buildBatchSizes): `TreeSet<>(List.of(25, 50, 250, 500, 1000, 5000, 10000))`.
   - `multilang_ports/java/src/test/java/benchmark/IndexBenchmarkTest.java:13-15`: same expected lists as Rust.
   - Result: 8 sizes → 24 build rows/language in scalability.csv (insert_* rows unchanged). `verify_format` compares pairs dynamically vs Go — no change.
   - No README/docs mention batch sizes (verified).

5. **Gates after edits**: pytest / mvn / cargo / go all green (tests now expect the new lists).

6. **Re-run benchmarks** (~2 h; results/*.csv are gitignored — verify only):
   - Python (~35 min), Go (~13 min), Rust (~30 min), Java (~50 min), sequential.
   - Watch: Python json @10000 RAM peak ~3-4 GB (67,7 M postings); Java heap — if OOM, raise `-Xmx` for the benchmark JVM; Mongo will hold ~67 M postings in `search_engine_benchmark` (several GB; drop DB after the run if desired).
   - `verify_format.py`: Go as reference for go/java/rust, Python `--format-only`.

7. **Publish snapshot**: copy CSVs → `docs/results/2026-10-02/{python,go,java,rust}/` (mirror 2026-09-30 layout) + verify_format against the snapshot.

8. **Commits** (English, imperative, atomic):
   - `feat: add mid-frequency terms to shared query workload` — queries.txt + Go queries test.
   - `feat: scale index build batches up to 10000 books` — 4 constants + go/java/rust batch-size tests.
   - `docs: update query count and sample claims in readmes` — 4 READMEs.
   - `docs: publish 2026-10-02 benchmark snapshots` — docs/results/2026-10-02/.
   - Push branch + `git push origin HEAD:develop` (ff) + `git fetch origin develop:develop`.

## Known notes (no action)
- Teammate's `insert_*` rows now batched (`68514e5`) — Python-only, not comparable to old snapshots.
- `44ee0a2` DB rename + `5d76a07` time-based lookup → 2026-10-02 numbers differ from 2026-09-30 beyond workload changes.
- `e1e90a1` restored folder-index parity (Windows reserved names — corpus has con/aux/nul/prn).
- Stale remote branches `chore/benchmark-prep`, `fix/core-requirements` have no unique commits (ignore).
- Runtime CSVs remain un-tracked per user decision; `insert_*` scalability rows keep sizes 10/100/1000/10000 (`SCALABILITY_BATCH_SIZES`, metadata) — unchanged.
