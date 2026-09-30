"""Shared fixtures for the datamart tests: a tiny time-based datalake and a SQLite metadata store."""

import pytest

from src.datamarts.metadata.storage import SQLiteStorage

BOOKS = {
    11: ("Alice's Adventures in Wonderland", "Lewis Carroll", "Alice fell down the rabbit hole."),
    84: ("Frankenstein; or, the modern prometheus", "Mary Wollstonecraft Shelley", "The creature and the monster."),
    1342: ("Pride and Prejudice", "Jane Austen", "Elizabeth met Darcy. The rabbit ran."),
}


@pytest.fixture
def datalake_dir(tmp_path):
    """A datalake holding the ``BOOKS`` in the time-based layout."""
    folder = tmp_path / "datalake" / "20250925" / "14"
    folder.mkdir(parents=True)
    for book_id, (title, author, body) in BOOKS.items():
        header = f"The Project Gutenberg eBook\n\nTitle: {title}\n\nAuthor: {author}\n\nLanguage: English\n"
        (folder / f"{book_id}_header.txt").write_text(header, encoding="utf-8")
        (folder / f"{book_id}_body.txt").write_text(body, encoding="utf-8")
    return tmp_path / "datalake"


@pytest.fixture
def metadata_storage(tmp_path):
    return SQLiteStorage(tmp_path / "metadata.db")
