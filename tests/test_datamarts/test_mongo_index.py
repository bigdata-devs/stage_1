import pytest

from src.datamarts.inverted_index.mongo_index import (
    DEFAULT_COLLECTION_NAME,
    build_index,
    get_collection,
    is_available,
    load_index,
    query_index,
    save_index,
    update_book,
)

MONGO_URI = "mongodb://localhost:27017"
TEST_DATABASE_NAME = "search_engine_test"

pytestmark = pytest.mark.skipif(
    not is_available(MONGO_URI),
    reason="MongoDB is not available at mongodb://localhost:27017",
)


@pytest.fixture
def collection():
    client_collection = get_collection(
        MONGO_URI,
        TEST_DATABASE_NAME,
        DEFAULT_COLLECTION_NAME,
    )
    client_collection.delete_many({})
    yield client_collection
    client_collection.database.command("dropDatabase")


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
        index = build_index({})
        assert index == {}


class TestSaveAndLoadIndex:
    def test_roundtrip(self, collection):
        index = {"cat": [1, 2], "dog": [1]}

        save_index(index, collection)
        loaded = load_index(collection)

        assert loaded == index

    def test_replaces_previous_index(self, collection):
        save_index({"old": [1]}, collection)
        save_index({"new": [2]}, collection)

        loaded = load_index(collection)

        assert loaded == {"new": [2]}

    def test_empty_index_clears_collection(self, collection):
        save_index({"cat": [1]}, collection)
        save_index({}, collection)

        assert load_index(collection) == {}

    def test_document_schema(self, collection):
        save_index({"adventure": [5, 12, 42, 1342]}, collection)

        document = collection.find_one({"term": "adventure"})

        assert document["term"] == "adventure"
        assert document["postings"] == [5, 12, 42, 1342]


class TestQueryIndex:
    def test_finds_existing_term(self, collection):
        save_index({"adventure": [1, 2]}, collection)
        assert query_index("adventure", collection) == [1, 2]

    def test_returns_empty_for_missing_term(self, collection):
        assert query_index("nonexistent", collection) == []


class TestUpdateBook:
    def test_adds_new_term(self, collection):
        update_book(7, ["dragon", "castle"], collection)
        assert query_index("dragon", collection) == [7]
        assert query_index("castle", collection) == [7]

    def test_merges_book_ids_sorted(self, collection):
        save_index({"cat": [1, 5]}, collection)
        update_book(3, ["cat"], collection)
        assert query_index("cat", collection) == [1, 3, 5]

    def test_does_not_duplicate_book_id(self, collection):
        update_book(1, ["cat"], collection)
        update_book(1, ["cat"], collection)
        assert query_index("cat", collection) == [1]
