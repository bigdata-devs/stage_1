import json
from pathlib import Path

from src.datamarts.inverted_index.postings import build_postings, merge_postings
from src.utils.atomic_file import write_text_atomically


def build_index(books: dict[int, list[str]]) -> dict[str, list[int]]:
    return build_postings(books)


def save_index(index: dict, output_path: Path) -> None:
    """Replaces the index file atomically: an interrupted save leaves the previous index intact."""
    write_text_atomically(output_path, json.dumps(index, ensure_ascii=False, indent=2))


def load_index(index_path: Path) -> dict:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def add_book(book_id: int, tokens: list[str], index_path: Path) -> None:
    """Adds one book to the index file, creating it if needed; re-adding a book is harmless."""
    index = load_index(index_path) if index_path.exists() else {}
    book_postings = build_postings({book_id: tokens})
    save_index(merge_postings(index, book_postings), index_path)
