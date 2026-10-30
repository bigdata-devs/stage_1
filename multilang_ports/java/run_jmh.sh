#!/usr/bin/env bash
# Runs the Java JMH micro-benchmarks and stores the JSON report beside the
# Java harness results. Only Java uses this protocol (warm-up iterations and
# forks come from JMH); the harness rows that feed the cross-language charts
# must never be mixed with these numbers.
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPOSITORY_ROOT"

mvn -q -f multilang_ports/java/pom.xml -DskipTests package
mkdir -p benchmarks_results/java
java -jar multilang_ports/java/target/metadata-processor-1.0.jar \
    -foe true -prof gc -rf json -rff benchmarks_results/java/jmh_results.json
