from collections import defaultdict
from pathlib import Path


def build_index(books: dict[int, list[str]], output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    postings: dict[str, set[int]] = defaultdict(set)
    for book_id, tokens in books.items():
        for token in tokens:
            postings[token].add(book_id)
    _write_all_terms(postings, output_path)


def save_index(index: dict[str, list[int]], output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    postings = {term: set(ids) for term, ids in index.items()}
    _write_all_terms(postings, output_path)


def load_index(index_path: Path) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for letter_dir in sorted(index_path.iterdir()):
        if not letter_dir.is_dir():
            continue
        for term_file in sorted(letter_dir.glob("*.txt")):
            term = term_file.stem
            book_ids = _read_term_file(term_file)
            index[term] = book_ids
    return index


def query_index(term: str, index_path: Path) -> list[int]:
    letter = term[0].upper()
    term_file = index_path / letter / f"{term}.txt"
    if not term_file.exists():
        return []
    return _read_term_file(term_file)


def _write_all_terms(postings: dict[str, set[int]], output_path: Path) -> None:
    by_letter: dict[str, dict[str, list[int]]] = defaultdict(dict)
    for term, book_ids in postings.items():
        letter = term[0].upper()
        by_letter[letter][term] = sorted(book_ids)
    for letter, terms in by_letter.items():
        letter_dir = output_path / letter
        letter_dir.mkdir(parents=True, exist_ok=True)
        for term, book_ids in terms.items():
            term_file = letter_dir / f"{term}.txt"
            content = "\n".join(str(bid) for bid in book_ids) + "\n"
            term_file.write_text(content, encoding="utf-8")


def _read_term_file(term_file: Path) -> list[int]:
    content = term_file.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return [int(line) for line in content.splitlines()]
