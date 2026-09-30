import pytest

from src.datamarts.metadata.book_processor import process_book, process_datalake


class TestProcessBook:
    def test_reads_metadata_from_the_datalake(self, datalake_dir, metadata_storage):
        process_book(1342, metadata_storage, datalake_dir)
        book = metadata_storage.find_book_by_id(1342)
        assert (book.title, book.author, book.language) == ("Pride and Prejudice", "Jane Austen", "en")
        assert book.body_path == (datalake_dir / "20250925" / "14" / "1342_body.txt").resolve()
        assert book.header_path.name == "1342_header.txt"

    def test_missing_book_raises(self, datalake_dir, metadata_storage):
        with pytest.raises(FileNotFoundError):
            process_book(7, metadata_storage, datalake_dir)

    def test_never_downloads(self, datalake_dir, metadata_storage, monkeypatch):
        import requests

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: pytest.fail("book_processor must not download"))
        process_book(84, metadata_storage, datalake_dir)


class TestProcessDatalake:
    def test_stores_every_book(self, datalake_dir, metadata_storage):
        process_datalake(metadata_storage, datalake_dir)
        assert [book.book_id for book in metadata_storage.list_books()] == [11, 84, 1342]
        assert [book.book_id for book in metadata_storage.find_books_by_author("carroll")] == [11]
