from pymongo import ASCENDING, MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import ServerSelectionTimeoutError

from src.datamarts.inverted_index.postings import build_postings

DEFAULT_MONGO_URI = "mongodb://localhost:27017"
DEFAULT_DATABASE_NAME = "search_engine"
DEFAULT_COLLECTION_NAME = "inverted_index"
CONNECTION_TIMEOUT_MS = 2000


def get_collection(
    mongo_uri: str = DEFAULT_MONGO_URI,
    database_name: str = DEFAULT_DATABASE_NAME,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Collection:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=CONNECTION_TIMEOUT_MS)
    collection = client[database_name][collection_name]
    collection.create_index([("term", ASCENDING)], unique=True)
    return collection


def is_available(mongo_uri: str = DEFAULT_MONGO_URI) -> bool:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=CONNECTION_TIMEOUT_MS)
    try:
        client.admin.command("ping")
        return True
    except ServerSelectionTimeoutError:
        return False


def build_index(books: dict[int, list[str]]) -> dict[str, list[int]]:
    return build_postings(books)


def save_index(index: dict[str, list[int]], collection: Collection) -> None:
    collection.delete_many({})
    documents = [
        {"term": term, "postings": book_ids} for term, book_ids in index.items()
    ]
    if documents:
        collection.insert_many(documents)


def load_index(collection: Collection) -> dict[str, list[int]]:
    return {
        document["term"]: document["postings"]
        for document in collection.find({}, {"_id": 0, "term": 1, "postings": 1})
    }


def query_index(term: str, collection: Collection) -> list[int]:
    document = collection.find_one({"term": term}, {"_id": 0, "postings": 1})
    if document is None:
        return []
    return document["postings"]


def update_book(book_id: int, tokens: list[str], collection: Collection) -> None:
    """Adds one book to every posting list it belongs to with a single unordered bulk write.

    Each term becomes one upserting pipeline update that merges the book ID
    into the postings and keeps them sorted, so the whole book costs one
    round trip (split into batches by the driver) instead of two per term.
    Re-adding a book is harmless.
    """
    operations = [_add_book_to_term(term, book_id) for term in sorted(set(tokens))]
    if operations:
        collection.bulk_write(operations, ordered=False)


def _add_book_to_term(term: str, book_id: int) -> UpdateOne:
    """Builds the upsert that inserts ``book_id`` into the sorted, duplicate-free postings of ``term``."""
    merged_postings = {"$setUnion": [{"$ifNull": ["$postings", []]}, [book_id]]}
    sorted_postings = {"$sortArray": {"input": merged_postings, "sortBy": 1}}
    return UpdateOne({"term": term}, [{"$set": {"postings": sorted_postings}}], upsert=True)
