#!/usr/bin/env bash
# Runs the full benchmark tournament and refreshes the committed snapshot in
# benchmarks_results/. The phases are ordered so that no timing is taken
# before the languages are proven equivalent:
#
#   0 equivalence  cross-language canonical files compared byte for byte
#   1 download     one probe round per language, round-robin over BENCH_DOWNLOAD_ROUNDS
#                  rounds, so every language downloads at the same hours
#   2 benchmarks   go, rust, java (with -results) and python (copied afterwards);
#                  java also runs its JMH micro-benchmarks
#   3 verify       format check for python/go, full row parity for rust/java
#   4 environment  hardware, toolchain and dataset record
#   5 charts       the shared visualization suite
#
# Every timed phase runs pinned to one logical core (taskset) with a single
# scheduler thread per runtime (GOMAXPROCS=1 for Go, ActiveProcessorCount=1 for
# Java), so the CPU percentages of the four languages describe the same budget.
# Override with BENCH_CPU_CORE / BENCH_DOWNLOAD_ROUNDS.
#
# Prerequisites: python3, go, rustc+cargo and java+maven on PATH. A local
# mongod is picked up automatically by every port when reachable and skipped
# consistently otherwise. Run it from anywhere: scripts/run_tournament.sh
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

LOG_DIRECTORY="${BENCH_LOG_DIR:-$HOME/.cache/stage_1_benchmarks/bench_logs}"
mkdir -p "$LOG_DIRECTORY"

CPU_CORE="${BENCH_CPU_CORE:-4}"
DOWNLOAD_ROUNDS="${BENCH_DOWNLOAD_ROUNDS:-5}"
GO_BINARY="$LOG_DIRECTORY/go_bench"
RUST_BINARY="target/release/bench"
JAVA_MAIN_CLASS="benchmark.Main"
JAVA_MAVEN_OPTS="${MAVEN_OPTS:--Xmx5g -XX:ActiveProcessorCount=1}"

phase() {
    echo "[tournament] $1 ($(date -u +%H:%M:%S))"
    echo "PHASE $1 $(date)" >> "$LOG_DIRECTORY/progress.log"
}

clean_previous_results() {
    rm -f benchmarks_results/go/*.csv benchmarks_results/rust/*.csv
    rm -f benchmarks_results/java/*.csv
    rm -f src/utils/benchmarks/results/*.csv
}

run_equivalence() {
    phase "equivalence"
    python3 -m src.utils.benchmarks.equivalence_check
}

# --- download probe: one round per language, interleaved --------------------
run_download_round() {
    local round="$1"
    echo "[tournament] download round $round/$DOWNLOAD_ROUNDS ($(date -u +%H:%M:%S))"
    (cd multilang_ports/go && GOMAXPROCS=1 taskset -c "$CPU_CORE" "$GO_BINARY" bench \
        -download-only -results ../../benchmarks_results/go) \
        2>&1 | tee -a "$LOG_DIRECTORY/download.log"
    (cd multilang_ports/rust && taskset -c "$CPU_CORE" "$RUST_BINARY" bench \
        -download-only -results ../../benchmarks_results/rust) \
        2>&1 | tee -a "$LOG_DIRECTORY/download.log"
    (cd multilang_ports/java && MAVEN_OPTS="$JAVA_MAVEN_OPTS" taskset -c "$CPU_CORE" mvn -q compile exec:java \
        "-Dexec.mainClass=$JAVA_MAIN_CLASS" \
        "-Dexec.args=bench -download-only -results ../../benchmarks_results/java") \
        2>&1 | tee -a "$LOG_DIRECTORY/download.log"
    taskset -c "$CPU_CORE" python3 -m src.utils.benchmarks.download_probe \
        2>&1 | tee -a "$LOG_DIRECTORY/download.log"
}

build_download_binaries() {
    (cd multilang_ports/go && go build -o "$GO_BINARY" .)
    (cd multilang_ports/rust && cargo build --release --bin bench)
    (cd multilang_ports/java && MAVEN_OPTS="$JAVA_MAVEN_OPTS" mvn -q compile)
}

run_download_phase() {
    phase "download"
    build_download_binaries
    for round in $(seq 1 "$DOWNLOAD_ROUNDS"); do
        run_download_round "$round"
    done
    cp src/utils/benchmarks/results/*.csv benchmarks_results/python/
}

# --- timed benchmark phases ------------------------------------------------
run_go_benchmark() {
    phase "go"
    (cd multilang_ports/go && GOMAXPROCS=1 taskset -c "$CPU_CORE" "$GO_BINARY" bench \
        -results ../../benchmarks_results/go) \
        2>&1 | tee "$LOG_DIRECTORY/go.log"
}

run_rust_benchmark() {
    phase "rust"
    (cd multilang_ports/rust && cargo build --release --bin bench \
        && taskset -c "$CPU_CORE" "$RUST_BINARY" bench -results ../../benchmarks_results/rust) \
        2>&1 | tee "$LOG_DIRECTORY/rust.log"
}

run_java_benchmark() {
    phase "java"
    # exec:java runs inside Maven's JVM, whose ergonomic default (~2 GB on an
    # 8 GB host) is too small for the 10000-book JSON build; 5 GB leaves room
    # for mongod and the operating system on the same machine. The same JVM
    # reports ActiveProcessorCount=1 so its CPU budget matches the other ports.
    (cd multilang_ports/java && MAVEN_OPTS="$JAVA_MAVEN_OPTS" taskset -c "$CPU_CORE" mvn -q compile exec:java \
        "-Dexec.mainClass=$JAVA_MAIN_CLASS" \
        "-Dexec.args=bench -results ../../benchmarks_results/java") \
        2>&1 | tee "$LOG_DIRECTORY/java.log"
}

run_java_micro_benchmarks() {
    phase "java jmh"
    ./multilang_ports/java/run_jmh.sh 2>&1 | tee "$LOG_DIRECTORY/java_jmh.log"
}

run_python_benchmark() {
    phase "python"
    taskset -c "$CPU_CORE" python3 -m src.utils.benchmarks.benchmark_implementations \
        2>&1 | tee "$LOG_DIRECTORY/python.log"
    cp src/utils/benchmarks/results/*.csv benchmarks_results/python/
}

verify_snapshots() {
    phase "verify"
    python3 src/utils/benchmarks/verify_format.py benchmarks_results/go --format-only
    python3 src/utils/benchmarks/verify_format.py benchmarks_results/python --format-only
    python3 src/utils/benchmarks/verify_format.py benchmarks_results/rust
    python3 src/utils/benchmarks/verify_format.py benchmarks_results/java
}

mongo_version_record() {
    if command -v mongod > /dev/null 2>&1; then
        mongod --version 2>&1 | head -1
    elif docker ps --format '{{.Names}}' 2>/dev/null | grep -qx stage1-mongodb; then
        echo "mongod $(docker exec stage1-mongodb mongod --version 2>&1 | head -1) (docker)"
    else
        echo "mongod not reachable"
    fi
}

record_environment() {
    phase "environment"
    {
        echo "# Generated by scripts/run_tournament.sh; do not edit."
        echo "generated_at_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "git_commit: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
        echo "kernel: $(uname -a)"
        echo "cpu_model: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ *//')"
        echo "cpu_cores: $(nproc)"
        echo "cpu_affinity: pinned to logical core $CPU_CORE with taskset; GOMAXPROCS=1 and -XX:ActiveProcessorCount=1"
        echo "memory_total_kb: $(awk '/MemTotal/ {print $2}' /proc/meminfo)"
        echo "disk_free: $(df -h . | awk 'NR==2 {print $4}')"
        echo "dataset_books: $(ls data_source/bodies | wc -l)"
        echo "dataset_size: $(du -sh data_source | cut -f1)"
        echo "python: $(python3 --version 2>&1)"
        echo "go: $(go version 2>&1)"
        echo "rustc: $(rustc --version 2>&1)"
        echo "cargo: $(cargo --version 2>&1)"
        echo "java: $(java -version 2>&1 | head -1)"
        echo "maven: $(mvn -version 2>&1 | head -1)"
        echo "mongodb: $(mongo_version_record)"
    } > benchmarks_results/environment.txt
}

render_charts() {
    phase "charts"
    python3 -m src.visualizations.main --output-dir charts
}

clean_previous_results
run_equivalence
run_download_phase
run_go_benchmark
run_rust_benchmark
run_java_benchmark
run_java_micro_benchmarks
run_python_benchmark
verify_snapshots
record_environment
render_charts
phase "done"
