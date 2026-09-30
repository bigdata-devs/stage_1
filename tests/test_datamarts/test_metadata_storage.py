import sqlite3
from pathlib import Path

import pytest

from src.datamarts.metadata.book_metadata import BookMetadata, BookNotFoundError, resolve_stored_path, to_stored_path
from src.datamarts.metadata.storage import SQLiteStorage
from src.utils.paths import PROJECT_ROOT


def make_metadata(book_id, title, author, folder=Path("/data/lake")):
    return BookMetadata(book_id, title, author, "en", "2025-09-25 14:00:00",
                        folder / f"{book_id}_header.txt", folder / f"{book_id}_body.txt")


@pytest.fixture
def filled_storage(metadata_storage):
    metadata_storage.save(make_metadata(1342, "Pride and Prejudice", "Jane Austen"))
    metadata_storage.save(make_metadata(105, "Persuasion", "Jane Austen"))
    metadata_storage.save(make_metadata(84, "Frankenstein", "Mary Wollstonecraft Shelley"))
    return metadata_storage


class TestSaveAndFind:
    def test_find_by_id_returns_paths(self, filled_storage):
        book = filled_storage.find_book_by_id(1342)
        assert book.title == "Pride and Prejudice"
        assert book.body_path == Path("/data/lake/1342_body.txt").resolve()

    def test_find_missing_id_raises(self, filled_storage):
        with pytest.raises(BookNotFoundError):
            filled_storage.find_book_by_id(999)

    def test_filters_by_author_case_insensitively(self, filled_storage):
        assert [book.book_id for book in filled_storage.find_books_by_author("austen")] == [105, 1342]

    def test_finds_path_by_title(self, filled_storage):
        [book] = filled_storage.find_books_by_title("frankenstein")
        assert book.body_path.name == "84_body.txt"

    def test_like_wildcards_are_literal(self, filled_storage):
        assert filled_storage.find_books_by_author("%") == []
        assert filled_storage.find_books_by_title("_") == []

    def test_saving_again_replaces_the_record(self, filled_storage):
        filled_storage.save(make_metadata(84, "Frankenstein (revised)", "Mary Shelley"))
        assert filled_storage.find_book_by_id(84).title == "Frankenstein (revised)"
        assert len(filled_storage.list_books()) == 3


class TestSchemaMigration:
    def test_adds_path_columns_to_old_databases(self, tmp_path):
        db_path = tmp_path / "old.db"
        with sqlite3.connect(db_path) as connection:
            connection.execute("CREATE TABLE books (book_id INTEGER PRIMARY KEY, title TEXT, author TEXT, "
                               "language TEXT, capture_date TEXT)")
            connection.execute("INSERT INTO books VALUES (1, 'Old', 'Someone', 'English', '2025')")
        connection.close()
        storage = SQLiteStorage(db_path)
        assert storage.list_books() == []
        storage.save(make_metadata(1, "Old", "Someone"))
        assert storage.find_book_by_id(1).body_path.name == "1_body.txt"


class TestStoredPaths:
    def test_paths_inside_the_project_are_stored_relative(self):
        body_path = PROJECT_ROOT / "datalake" / "20250925" / "14" / "5_body.txt"
        assert to_stored_path(body_path) == "datalake/20250925/14/5_body.txt"
        assert resolve_stored_path("datalake/20250925/14/5_body.txt") == body_path

    def test_paths_outside_the_project_stay_absolute(self, tmp_path):
        stored = to_stored_path(tmp_path / "5_body.txt")
        assert Path(stored).is_absolute()
        assert resolve_stored_path(stored) == (tmp_path / "5_body.txt").resolve()
