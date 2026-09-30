import json

import pytest

from src.utils import atomic_file

from src.datamarts.inverted_index.json_index import add_book, build_index, save_index, load_index


class TestBuildIndex:
    def test_single_book(self):
        books = {1: ["cat", "dog", "cat"]}
        index = build_index(books)
        assert index == {"cat": [1], "dog": [1]}

    def test_multiple_books(self):
        books = {1: ["cat", "dog"], 2: ["cat", "bird"]}
        index = build_index(books)
        assert index["cat"] == [1, 2]
        assert index["dog"] == [1]
        assert index["bird"] == [2]

    def test_book_ids_are_sorted(self):
        books = {3: ["cat"], 1: ["cat"], 2: ["cat"]}
        index = build_index(books)
        assert index["cat"] == [1, 2, 3]

    def test_no_duplicate_book_ids(self):
        books = {1: ["cat", "cat", "cat"]}
        index = build_index(books)
        assert index["cat"] == [1]

    def test_empty_input(self):
        books = {}
        index = build_index(books)
        assert index == {}


class TestSaveAndLoadIndex:
    def test_roundtrip(self, tmp_path):
        index = {"cat": [1, 2], "dog": [1]}
        path = tmp_path / "test_index.json"

        save_index(index, path)
        loaded = load_index(path)

        assert loaded == index

    def test_creates_parent_directory(self, tmp_path):
        index = {"cat": [1]}
        path = tmp_path / "nested" / "dir" / "index.json"

        save_index(index, path)
        assert path.exists()

    def test_json_is_valid(self, tmp_path):
        index = {"hello": [1, 2, 3]}
        path = tmp_path / "index.json"

        save_index(index, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == index


class TestAddBook:
    def test_creates_index_file_for_first_book(self, tmp_path):
        path = tmp_path / "index.json"

        add_book(7, ["cat", "dog", "cat"], path)

        assert load_index(path) == {"cat": [7], "dog": [7]}

    def test_merges_postings_in_sorted_order(self, tmp_path):
        path = tmp_path / "index.json"
        save_index({"cat": [9], "owl": [9]}, path)

        add_book(3, ["cat", "dog"], path)

        assert load_index(path) == {"cat": [3, 9], "owl": [9], "dog": [3]}

    def test_adding_same_book_twice_is_harmless(self, tmp_path):
        path = tmp_path / "index.json"

        add_book(3, ["cat"], path)
        add_book(3, ["cat"], path)

        assert load_index(path) == {"cat": [3]}


class TestAtomicSave:
    def test_interrupted_save_keeps_previous_index(self, tmp_path, monkeypatch):
        path = tmp_path / "index.json"
        save_index({"cat": [1]}, path)

        def crash(*args, **kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(atomic_file, "_write_and_sync", crash)
        with pytest.raises(KeyboardInterrupt):
            add_book(2, ["dog"], path)
        assert load_index(path) == {"cat": [1]}
        assert sorted(item.name for item in tmp_path.iterdir()) == ["index.json"]
