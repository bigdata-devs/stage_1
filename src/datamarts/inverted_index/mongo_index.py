from pymongo import ASCENDING, MongoClient
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
    for term in set(tokens):
        collection.update_one(
            {"term": term},
            {"$addToSet": {"postings": book_id}},
            upsert=True,
        )
        _sort_postings(term, collection)


def _sort_postings(term: str, collection: Collection) -> None:
    collection.update_one(
        {"term": term},
        [{"$set": {"postings": {"$sortArray": {"input": "$postings", "sortBy": 1}}}}],
    )
