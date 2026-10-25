"""Cross-structure equivalence: the three index structures must answer every
query identically before their latencies are compared.

The same corpus is built into the JSON file, the folder index and (when the
server is up) MongoDB; every shared term plus a few absent terms is then
queried on each structure. A second pass adds the same new book to each
structure and re-checks, so incremental updates cannot diverge silently.
"""

import json

import pytest

from src.datamarts.inverted_index import json_index, folder_index
from src.datamarts.inverted_index.corpus import load_corpus
from src.datamarts.inverted_index.mongo_index import get_collection, is_available, query_index
from src.datamarts.inverted_index.mongo_index import save_index as save_mongo_index
from src.datamarts.inverted_index.mongo_index import update_book as update_mongo_book
from src.datamarts.metadata.book_processor import process_datalake
from src.utils.text_processor import process_text

ABSENT_TERMS = ["nonexistentterm", "zzz"]
NEW_BOOK_ID = 9999
NEW_BOOK_TOKENS = process_text("the white rabbit appeared again")
MONGO_TEST_DATABASE = "search_engine_structure_equivalence"


@pytest.fixture
def corpus_tokens(datalake_dir, metadata_storage):
    process_datalake(metadata_storage, datalake_dir)
    return load_corpus(metadata_storage)


@pytest.fixture
def json_structure(corpus_tokens, tmp_path):
    index_path = tmp_path / "inverted_index.json"
    index = json_index.build_index(corpus_tokens)
    json_index.save_index(index, index_path)
    return index_path


@pytest.fixture
def folder_structure(corpus_tokens, tmp_path):
    index_path = tmp_path / "inverted_index"
    folder_index.build_index(corpus_tokens, index_path)
    return index_path


@pytest.fixture
def mongo_structure(corpus_tokens):
    if not is_available():
        pytest.skip("MongoDB is not available at mongodb://localhost:27017")
    collection = get_collection(database_name=MONGO_TEST_DATABASE)
    collection.delete_many({})
    save_mongo_index(json_index.build_index(corpus_tokens), collection)
    yield collection
    collection.database.client.drop_database(MONGO_TEST_DATABASE)


def shared_terms(corpus_tokens):
    terms = sorted({term for tokens in corpus_tokens.values() for term in tokens})
    return terms + ABSENT_TERMS


def json_answers(index_path, terms):
    index = json.loads(index_path.read_text(encoding="utf-8"))
    return {term: index.get(term, []) for term in terms}


def folder_answers(index_path, terms):
    return {term: folder_index.query_index(term, index_path) for term in terms}


def mongo_answers(collection, terms):
    return {term: query_index(term, collection) for term in terms}


class TestStructureEquivalence:
    def test_json_and_folder_answer_every_query_identically(self, json_structure, folder_structure, corpus_tokens):
        terms = shared_terms(corpus_tokens)
        assert json_answers(json_structure, terms) == folder_answers(folder_structure, terms)

    def test_json_folder_and_mongo_answer_every_query_identically(
        self, json_structure, folder_structure, mongo_structure, corpus_tokens
    ):
        terms = shared_terms(corpus_tokens)
        answers = json_answers(json_structure, terms)
        assert answers == folder_answers(folder_structure, terms)
        assert answers == mongo_answers(mongo_structure, terms)

    def test_structures_stay_equivalent_after_the_same_update(
        self, json_structure, folder_structure, mongo_structure, corpus_tokens
    ):
        json_index.add_book(NEW_BOOK_ID, NEW_BOOK_TOKENS, json_structure)
        folder_index.update_book(NEW_BOOK_ID, NEW_BOOK_TOKENS, folder_structure)
        update_mongo_book(NEW_BOOK_ID, NEW_BOOK_TOKENS, mongo_structure)

        terms = shared_terms(corpus_tokens) + NEW_BOOK_TOKENS
        answers = json_answers(json_structure, terms)
        assert answers == folder_answers(folder_structure, terms)
        assert answers == mongo_answers(mongo_structure, terms)
        assert NEW_BOOK_ID in answers["rabbit"]
