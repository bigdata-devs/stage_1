"""Hierarchical folder inverted index: one ``<LETTER>/<term>.txt`` file per term, one book ID per line.

Windows reserves some file names (``CON``, ``PRN``, ``AUX``, ``NUL``,
``COM1``-``COM9``, ``LPT1``-``LPT9``) whatever their extension, so those terms
are stored with a trailing underscore (``con`` -> ``C/con_.txt``). Tokens only
contain letters, so the suffix can never clash with a real term.
"""

from pathlib import Path

from src.datamarts.inverted_index.postings import build_postings

TERM_FILE_SUFFIX = ".txt"
RESERVED_NAME_ESCAPE = "_"
WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)
_ENCODING = "utf-8"


def build_index(books: dict[int, list[str]], output_path: Path) -> None:
    save_index(build_postings(books), output_path)


def save_index(index: dict[str, list[int]], output_path: Path) -> None:
    output_path.mkdir(parents=True, exist_ok=True)
    for term, book_ids in index.items():
        _write_term_file(term_file_path(term, output_path), sorted(set(book_ids)))


def update_book(book_id: int, tokens: list[str], index_path: Path) -> None:
    """Adds one book to an existing index, rewriting only the files of the terms it contains."""
    for term in set(tokens):
        term_file = term_file_path(term, index_path)
        current_ids = _read_term_file(term_file) if term_file.exists() else []
        if book_id not in current_ids:
            _write_term_file(term_file, sorted({*current_ids, book_id}))


def load_index(index_path: Path) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for letter_dir in sorted(index_path.iterdir()):
        if not letter_dir.is_dir():
            continue
        for term_file in sorted(letter_dir.glob(f"*{TERM_FILE_SUFFIX}")):
            index[term_from_file_name(term_file.name)] = _read_term_file(term_file)
    return index


def query_index(term: str, index_path: Path) -> list[int]:
    term_file = term_file_path(term, index_path)
    if not term_file.exists():
        return []
    return _read_term_file(term_file)


def term_file_path(term: str, index_path: Path) -> Path:
    """Returns ``<index_path>/<FIRST LETTER>/<file name>`` for a term."""
    return index_path / term[0].upper() / term_file_name(term)


def term_file_name(term: str) -> str:
    """Returns the file name of a term, escaping names that Windows reserves."""
    if term.lower() in WINDOWS_RESERVED_NAMES:
        return f"{term}{RESERVED_NAME_ESCAPE}{TERM_FILE_SUFFIX}"
    return f"{term}{TERM_FILE_SUFFIX}"


def term_from_file_name(file_name: str) -> str:
    """Reverses ``term_file_name``."""
    stem = file_name.removesuffix(TERM_FILE_SUFFIX)
    unescaped = stem.removesuffix(RESERVED_NAME_ESCAPE)
    if unescaped != stem and unescaped.lower() in WINDOWS_RESERVED_NAMES:
        return unescaped
    return stem


def _write_term_file(term_file: Path, book_ids: list[int]) -> None:
    term_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{book_id}\n" for book_id in book_ids)
    term_file.write_text(content, encoding=_ENCODING)


def _read_term_file(term_file: Path) -> list[int]:
    content = term_file.read_text(encoding=_ENCODING).strip()
    if not content:
        return []
    return [int(line) for line in content.splitlines()]
