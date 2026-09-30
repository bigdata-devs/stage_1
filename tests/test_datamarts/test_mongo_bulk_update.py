"""Server-free checks of the requests ``mongo_index.update_book`` sends (behaviour is tested against MongoDB in test_mongo_index)."""

from pymongo import UpdateOne

from src.datamarts.inverted_index.mongo_index import update_book


class RecordingCollection:
    """Stands in for a pymongo Collection and records every request."""

    def __init__(self):
        self.requests = []

    def bulk_write(self, operations, ordered=True):
        self.requests.append(("bulk_write", list(operations), ordered))

    def update_one(self, *args, **kwargs):
        self.requests.append(("update_one", args, kwargs))


def expected_update(term, book_id):
    merged = {"$setUnion": [{"$ifNull": ["$postings", []]}, [book_id]]}
    return UpdateOne({"term": term}, [{"$set": {"postings": {"$sortArray": {"input": merged, "sortBy": 1}}}}], upsert=True)


class TestUpdateBookRequests:
    def test_sends_one_bulk_write_for_the_whole_book(self):
        collection = RecordingCollection()
        update_book(7, ["castle", "dragon", "castle", "moat"], collection)
        assert len(collection.requests) == 1
        name, operations, ordered = collection.requests[0]
        assert name == "bulk_write"
        assert ordered is False
        assert operations == [expected_update(term, 7) for term in ["castle", "dragon", "moat"]]

    def test_book_without_tokens_sends_nothing(self):
        collection = RecordingCollection()
        update_book(7, [], collection)
        assert collection.requests == []
