"""Equivalence mode of the Python port: writes the canonical file that the
cross-language checker compares byte for byte.

It reuses the same tokenizer (text_processor), the same postings builder
(datamarts.postings) and the same query intersection as the timed experiments,
so a file identical to the other languages' proves the harness measures the
same work everywhere. Timing results are meaningless until this check passes.
"""

import argparse
from pathlib import Path

from src.datamarts.inverted_index import json_index
from src.utils.body_files import read_book_body
from src.utils.benchmarks.queries import load_queries
from src.utils.text_processor import process_text

TOKENS_PREFIX = "tokens"
POSTINGS_PREFIX = "postings"
QUERY_PREFIX = "query"


def run(bodies_directory: Path, book_ids_file: Path, queries_file: Path, output_file: Path) -> None:
    """Writes the canonical equivalence file for this language."""
    book_ids = parse_book_ids(book_ids_file)
    tokenized = tokenize_books(book_ids, bodies_directory)
    index = json_index.build_index(tokenized)
    queries = load_queries(queries_file)
    with output_file.open("w", encoding="utf-8", newline="\n") as output:
        write_token_lines(output, tokenized)
        write_postings_lines(output, index)
        write_query_lines(output, queries, index)


def parse_book_ids(book_ids_file: Path) -> list[int]:
    lines = book_ids_file.read_text(encoding="utf-8").splitlines()
    return [int(line.strip()) for line in lines if line.strip()]


def tokenize_books(book_ids: list[int], bodies_directory: Path) -> dict[int, list[str]]:
    return {
        book_id: process_text(read_book_body(book_id, bodies_directory))
        for book_id in book_ids
    }


def write_token_lines(output, tokenized: dict[int, list[str]]) -> None:
    for book_id, tokens in tokenized.items():
        output.write(f"{TOKENS_PREFIX}\t{book_id}\t" + "\t".join(tokens) + "\n")


def write_postings_lines(output, index: dict[str, list[int]]) -> None:
    for term in sorted(index):
        book_ids = ",".join(str(book_id) for book_id in index[term])
        output.write(f"{POSTINGS_PREFIX}\t{term}\t{book_ids}\n")


def write_query_lines(output, queries: list[list[str]], index: dict[str, list[int]]) -> None:
    for ordinal, terms in enumerate(queries, start=1):
        book_ids = ",".join(str(book_id) for book_id in matching_documents(index, terms))
        suffix = f"\t{book_ids}" if book_ids else ""
        output.write(f"{QUERY_PREFIX}\t{ordinal}{suffix}\n")


def matching_documents(index: dict[str, list[int]], terms: list[str]) -> list[int]:
    matched = set(index.get(terms[0], []))
    for term in terms[1:]:
        matched &= set(index.get(term, []))
        if not matched:
            break
    return sorted(matched)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bodies_directory", type=Path)
    parser.add_argument("book_ids_file", type=Path)
    parser.add_argument("queries_file", type=Path)
    parser.add_argument("output_file", type=Path)
    arguments = parser.parse_args()
    run(arguments.bodies_directory, arguments.book_ids_file,
        arguments.queries_file, arguments.output_file)


if __name__ == "__main__":
    main()
