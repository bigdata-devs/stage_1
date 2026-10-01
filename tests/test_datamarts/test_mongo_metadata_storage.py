"""Server-free checks of the requests ``MongoStorage`` sends: the ``book_id`` index and the batched upserts."""

from pathlib import Path

import pytest
from pymongo import ASCENDING, UpdateOne

from src.datamarts.metadata import storage as storage_module
from src.datamarts.metadata.book_metadata import BookMetadata, to_stored_path
from src.datamarts.metadata.storage import BATCH_SIZE, MongoStorage


class RecordingCollection:
    """Stands in for a pymongo Collection and records every request."""

    def __init__(self):
        self.indexes = []
        self.bulk_writes = []

    def create_index(self, keys, **options):
        self.indexes.append((keys, options))

    def bulk_write(self, operations):
        self.bulk_writes.append(list(operations))


class RecordingClient:
    """Stands in for a MongoClient whose databases only hold the recorded ``books`` collection."""

    def __init__(self, connection_string):
        self.books = RecordingCollection()

    def __getitem__(self, database_name):
        return {"books": self.books}


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setattr(storage_module, "MongoClient", RecordingClient)
    return MongoStorage("mongodb://recording")


def make_metadata(book_id):
    folder = Path("/data/lake")
    return BookMetadata(book_id, f"Book {book_id}", "Someone", "en", "2025-09-25 14:00:00",
                        folder / f"{book_id}_header.txt", folder / f"{book_id}_body.txt")


def expected_upsert(metadata):
    document = {
        "book_id": metadata.book_id,
        "title": metadata.title,
        "author": metadata.author,
        "language": metadata.language,
        "capture_date": metadata.capture_date,
        "header_path": to_stored_path(metadata.header_path),
        "body_path": to_stored_path(metadata.body_path),
    }
    return UpdateOne({"book_id": metadata.book_id}, {"$set": document}, upsert=True)


class TestMongoStorageRequests:
    def test_creates_a_unique_index_on_book_id(self, storage):
        assert storage.collection.indexes == [([("book_id", ASCENDING)], {"unique": True})]

    def test_upserts_each_record_by_book_id(self, storage):
        metadata = make_metadata(84)
        storage.save(metadata)
        assert storage.collection.bulk_writes == [[expected_upsert(metadata)]]

    def test_sends_one_bulk_write_per_batch(self, storage):
        storage.save_many(make_metadata(book_id) for book_id in range(BATCH_SIZE + 1))
        assert [len(operations) for operations in storage.collection.bulk_writes] == [BATCH_SIZE, 1]

    def test_empty_batch_sends_nothing(self, storage):
        storage.save_many([])
        assert storage.collection.bulk_writes == []
