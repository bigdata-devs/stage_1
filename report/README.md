# Stage 1 Benchmarking Report (LaTeX)

The report is a plain `article` document split into one `.tex` file per
section under `sections/`. It compiles with any LaTeX distribution; the
repository uses [Tectonic](https://tectonic-typesetting.github.io/):

```bash
cd report
tectonic main.tex          # writes main.pdf
```

## Figures

Figures resolve from two paths, in this order:

1. `../charts/` --- the figures rendered by the benchmark tournament
   (`src/visualizations/main.py`); regenerate them with
   `./scripts/run_tournament.sh` (phase 4) or by running the visualizations
   module directly.
2. `figures/` --- optional local copies (used on Overleaf).

The interactive Sankey diagram (`charts/sankey/storage_sankey.html`) is
referenced as a repository artifact, not embedded in the PDF.

## Uploading to Overleaf

1. Zip the contents of `report/` **plus** the `charts/` directory, keeping
   the layout (`main.tex` next to a `charts/` folder), and upload the zip;
   or
2. create an Overleaf project, upload `main.tex` and `sections/`, then drag
   the files of `charts/` into a `charts/` folder in the project tree.

`main.tex` is the compile root. Numbers still to be filled from the final
tournament run are printed in red as `[TODO: ...]` by the `\pending{}`
macro, so an unfinished figure cannot ship unnoticed.

## Files

| File | Content |
| --- | --- |
| `main.tex` | Preamble, macros, section order |
| `sections/01_introduction.tex` | Objectives and scope of the claims |
| `sections/02_architecture.tex` | Three layers + TikZ pipeline diagram |
| `sections/03_design_decisions.tex` | Tokenisation and metadata contracts |
| `sections/04_methodology.tex` | Host, runtimes, metrics, workload, timing |
| `sections/05_equivalence.tex` | Cross-language and cross-structure gates |
| `sections/06_language_performance.tex` | Radar and throughput/latency overview |
| `sections/07_datalake.tex` | Layouts: throughput, lookup, discovery, storage, recovery |
| `sections/08_inverted_index.tex` | Scalability, queries, updates, memory/disk |
| `sections/09_jmh.tex` | JMH micro-benchmarks (Java only) |
| `sections/10_conclusions.tex` | Scoped selection for Stage 2 |
| `sections/11_limitations.tex` | Machine, runtime, cache, workload, timing |
| `sections/12_reproducibility.tex` | One command, chart-to-artifact map |
| `sections/13_comment_matrix.tex` | The 33 correction comments → sections |
