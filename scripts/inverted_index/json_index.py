import json
from pathlib import Path


def build_index(books: dict[int, list[str]]) -> dict[str, list[int]]:
    index: dict[str, set[int]] = {}
    for book_id, tokens in books.items():
        for token in tokens:
            if token not in index:
                index[token] = set()
            index[token].add(book_id)
    return {term: sorted(ids) for term, ids in index.items()}


def save_index(index: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def load_index(index_path: Path) -> dict:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)
