import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from inverted_index.json_index import build_index, save_index, load_index


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
