"""Shared parser for the benchmark query workload (queries.txt).

Every language port parses this same file with the same rules; the equivalence
checker relies on all of them producing identical query lists, and the Python
timed experiments and the equivalence mode share this single implementation so
the workload cannot drift between them.
"""

from pathlib import Path


def load_queries(path: Path) -> list[list[str]]:
    queries = parse_queries(path.read_text(encoding="utf-8"))
    if not queries:
        raise RuntimeError(f"{path} must define at least one query")
    return queries


def parse_queries(text: str) -> list[list[str]]:
    queries = []
    for line in text.splitlines():
        terms = line.partition("#")[0].split()
        if terms:
            queries.append(terms)
    return queries
