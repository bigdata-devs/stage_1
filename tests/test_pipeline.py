import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_inverted_index import discover_book_ids, read_book_body, BODIES_DIR
from shared.text_processor import process_text
from inverted_index.json_index import build_index, save_index, load_index

SAMPLE_BODIES = Path(__file__).parent.parent / "sample_data" / "bodies"


class TestDiscoverBookIds:
    def test_finds_all_books(self):
        ids = discover_book_ids(SAMPLE_BODIES)
        assert sorted(ids) == [11, 84, 174, 1342]

    def test_returns_sorted_list(self):
        ids = discover_book_ids(SAMPLE_BODIES)
        assert ids == sorted(ids)


class TestReadBookBody:
    def test_reads_existing_book(self):
        text = read_book_body(1342, SAMPLE_BODIES)
        assert len(text) > 0
        assert "pride" in text.lower()

    def test_raises_on_missing_book(self):
        try:
            read_book_body(99999, SAMPLE_BODIES)
            assert False, "Should have raised an exception"
        except FileNotFoundError:
            pass


class TestPipelineIntegration:
    def test_full_pipeline_produces_valid_index(self, tmp_path):
        book_ids = discover_book_ids(SAMPLE_BODIES)
        books = {}
        for book_id in book_ids:
            text = read_book_body(book_id, SAMPLE_BODIES)
            tokens = process_text(text)
            books[book_id] = tokens

        index = build_index(books)

        assert len(index) > 0
        for term, ids in index.items():
            assert isinstance(term, str)
            assert isinstance(ids, list)
            assert all(isinstance(bid, int) for bid in ids)
            assert ids == sorted(ids)

    def test_known_words_present(self):
        book_ids = discover_book_ids(SAMPLE_BODIES)
        books = {}
        for book_id in book_ids:
            text = read_book_body(book_id, SAMPLE_BODIES)
            tokens = process_text(text)
            books[book_id] = tokens

        index = build_index(books)

        assert "pride" in index
        assert "prejudice" in index
        assert 1342 in index["pride"]

    def test_stopwords_not_in_index(self):
        book_ids = discover_book_ids(SAMPLE_BODIES)
        books = {}
        for book_id in book_ids:
            text = read_book_body(book_id, SAMPLE_BODIES)
            tokens = process_text(text)
            books[book_id] = tokens

        index = build_index(books)

        assert "the" not in index
        assert "and" not in index
        assert "is" not in index

    def test_save_and_load_roundtrip(self, tmp_path):
        book_ids = discover_book_ids(SAMPLE_BODIES)
        books = {}
        for book_id in book_ids:
            text = read_book_body(book_id, SAMPLE_BODIES)
            tokens = process_text(text)
            books[book_id] = tokens

        index = build_index(books)
        output_path = tmp_path / "inverted_index.json"
        save_index(index, output_path)
        loaded = load_index(output_path)

        assert loaded == index
