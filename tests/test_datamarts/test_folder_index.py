import pytest

from src.datamarts.inverted_index.folder_index import (
    build_index,
    save_index,
    load_index,
    query_index,
    term_file_name,
    term_from_file_name,
    update_book,
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


class TestWindowsReservedNames:
    @pytest.mark.parametrize("term", ["con", "prn", "aux", "nul", "com1", "lpt9", "CON"])
    def test_reserved_names_get_a_suffix(self, term):
        assert term_file_name(term) == f"{term}_.txt"

    @pytest.mark.parametrize("term", ["cone", "auxiliary", "null", "console"])
    def test_ordinary_terms_are_unchanged(self, term):
        assert term_file_name(term) == f"{term}.txt"

    @pytest.mark.parametrize("term", ["con", "aux", "cone", "nul"])
    def test_file_names_round_trip(self, term):
        assert term_from_file_name(term_file_name(term)) == term

    def test_reserved_terms_are_saved_loaded_and_queried(self, tmp_path):
        index = {"con": [1], "aux": [2], "nul": [3], "cone": [4]}
        save_index(index, tmp_path)
        assert (tmp_path / "C" / "con_.txt").exists()
        assert not (tmp_path / "C" / "con.txt").exists()
        assert load_index(tmp_path) == index
        assert query_index("nul", tmp_path) == [3]


class TestUpdateBook:
    def test_creates_index_for_first_book(self, tmp_path):
        update_book(7, ["cat", "dog", "cat"], tmp_path)
        assert load_index(tmp_path) == {"cat": [7], "dog": [7]}

    def test_merges_into_existing_postings_in_order(self, tmp_path):
        save_index({"cat": [9], "owl": [9]}, tmp_path)
        update_book(3, ["cat", "con"], tmp_path)
        assert load_index(tmp_path) == {"cat": [3, 9], "con": [3], "owl": [9]}

    def test_adding_same_book_twice_is_harmless(self, tmp_path):
        update_book(3, ["cat"], tmp_path)
        update_book(3, ["cat"], tmp_path)
        assert query_index("cat", tmp_path) == [3]
