import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from inverted_index.folder_index import (
    build_index,
    save_index,
    load_index,
    query_index,
)


class TestBuildIndex:
    def test_creates_letter_directories(self, tmp_path):
        books = {1: ["adventure", "boat"]}
        build_index(books, tmp_path)
        assert (tmp_path / "A").is_dir()
        assert (tmp_path / "B").is_dir()

    def test_creates_term_files(self, tmp_path):
        books = {1: ["adventure", "boat"]}
        build_index(books, tmp_path)
        assert (tmp_path / "A" / "adventure.txt").exists()
        assert (tmp_path / "B" / "boat.txt").exists()

    def test_writes_book_ids(self, tmp_path):
        books = {1: ["cat"], 2: ["cat"]}
        build_index(books, tmp_path)
        content = (tmp_path / "C" / "cat.txt").read_text()
        assert "1\n" in content
        assert "2\n" in content

    def test_book_ids_are_sorted(self, tmp_path):
        books = {3: ["cat"], 1: ["cat"], 2: ["cat"]}
        build_index(books, tmp_path)
        content = (tmp_path / "C" / "cat.txt").read_text()
        lines = content.strip().split("\n")
        assert lines == ["1", "2", "3"]

    def test_no_duplicate_book_ids(self, tmp_path):
        books = {1: ["cat", "cat", "cat"]}
        build_index(books, tmp_path)
        content = (tmp_path / "C" / "cat.txt").read_text()
        lines = content.strip().split("\n")
        assert lines == ["1"]


class TestSaveIndex:
    def test_saves_from_dict(self, tmp_path):
        index = {"adventure": [1, 2], "boat": [1]}
        save_index(index, tmp_path)
        assert (tmp_path / "A" / "adventure.txt").exists()
        assert (tmp_path / "B" / "boat.txt").exists()

    def test_content_matches_dict(self, tmp_path):
        index = {"cat": [5, 10]}
        save_index(index, tmp_path)
        content = (tmp_path / "C" / "cat.txt").read_text()
        assert content.strip().split("\n") == ["5", "10"]


class TestLoadIndex:
    def test_roundtrip(self, tmp_path):
        original = {"adventure": [1, 2], "boat": [1], "cat": [3]}
        save_index(original, tmp_path)
        loaded = load_index(tmp_path)
        assert loaded == original

    def test_empty_directory(self, tmp_path):
        loaded = load_index(tmp_path)
        assert loaded == {}

    def test_skips_non_directories(self, tmp_path):
        (tmp_path / "file.txt").write_text("hello")
        loaded = load_index(tmp_path)
        assert loaded == {}


class TestQueryIndex:
    def test_finds_existing_term(self, tmp_path):
        index = {"adventure": [1, 2]}
        save_index(index, tmp_path)
        result = query_index("adventure", tmp_path)
        assert result == [1, 2]

    def test_returns_empty_for_missing_term(self, tmp_path):
        result = query_index("nonexistent", tmp_path)
        assert result == []

    def test_query_is_case_insensitive_on_filesystem(self, tmp_path):
        index = {"Adventures": [1]}
        save_index(index, tmp_path)
        result = query_index("Adventures", tmp_path)
        assert result == [1]
