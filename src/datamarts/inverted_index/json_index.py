import json
from pathlib import Path

from src.datamarts.inverted_index.postings import build_postings


def build_index(books: dict[int, list[str]]) -> dict[str, list[int]]:
    return build_postings(books)


def save_index(index: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def load_index(index_path: Path) -> dict:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)
