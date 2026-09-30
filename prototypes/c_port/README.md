# Archived — C port (frozen)

Frozen prototype of the Stage 1 data layer in C (inverted index and metadata
storage only; no datalake or benchmark runner was ever ported).

The benchmarking suite is standardized on exactly four languages: **Python**
(baseline), **Go**, **Rust** and **Java**. The C port was archived because
managing cross-platform build systems (Make/CMake) and heavy external
dependencies for text processing and I/O (`libcurl`, `libpcre`,
`libmongoc`) creates too much environment friction for the team across
different operating systems.

This code is kept for reference only. It is not built, tested or maintained;
all Datalake layout, Inverted Index structure and Benchmark Runner work must
keep 1:1 parity between Python, Go, Rust and Java.
