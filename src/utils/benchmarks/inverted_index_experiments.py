import logging
import shutil
import time
from pathlib import Path

from src.utils.benchmarks import (
    BYTES_PER_MB,
    aggregate_scalability,
    measure_operation,
    measure_disk_usage,
    calculate_statistics,
    save_scalability,
    save_updates,
    save_result,
    save_statistics,
    save_disk_usage,
)
from src.utils.benchmarks import data_source
from src.utils.benchmarks.artifacts import ARTIFACT_ROOT, BENCHMARK_MONGO_DATABASE
from src.utils.benchmarks.logging_setup import configure_logging
from src.utils.benchmarks.queries import load_queries
from src.utils.body_files import read_book_body
from src.utils.text_processor import process_text
from src.datamarts.inverted_index import json_index, folder_index

INDEX_OUTPUT_DIRECTORY = ARTIFACT_ROOT / "index"
JSON_INDEX_PATH = INDEX_OUTPUT_DIRECTORY / "inverted_index.json"
FOLDER_INDEX_PATH = INDEX_OUTPUT_DIRECTORY / "inverted_index"
QUERIES_PATH = Path(__file__).with_name("queries.txt")
BUILD_BATCH_SIZES = (25, 50, 250, 500, 1000, 5000, 10000)
BUILD_REPETITIONS_SCHEDULE = ((1000, 5), (5000, 3))
DEFAULT_BUILD_REPETITIONS = 2
QUERY_SAMPLE_TARGET = 100
SYNTHETIC_BOOK_ID_BASE = 900000
UPDATE_BASE_SIZES = (25, 50, 250, 500, 1000)
UPDATE_REPETITIONS = 5

def run():
    books = load_tokenized_books()
    logging.info("Loaded %s books for the index experiments", len(books))
    queries = load_shared_queries()
    structures = [JsonIndexStructure(), FolderIndexStructure()]
    skipped = []
    try:
        structures.append(create_mongo_structure())
    except (ImportError, ConnectionError) as error:
        logging.warning("SKIP mongo_index: %s", error)
        skipped.append("mongo_index")
    for structure in structures:
        run_structure_experiments(structure, books, queries)
    return skipped

def run_structure_experiments(structure, books, queries):
    logging.info("--- Inverted index structure: %s ---", structure.name)
    structure.reset()
    for batch_size in batch_sizes(len(books)):
        measure_build(structure, books, batch_size)
    structure.prepare_query()
    measure_query_performance(structure, queries)
    measure_update(structure, books)
    measure_update_scaling(structure, books)
    measure_storage_overhead(structure)

def measure_build(structure, books, batch_size):
    subset = build_subset(books, batch_size)
    samples = [
        measure_operation(lambda: structure.build_and_save(subset))
        for _ in range(build_repetitions(batch_size))
    ]
    save_scalability({
        "test_name": f"build_{structure.name}",
        "batch_size": batch_size,
        **aggregate_scalability(samples),
    })

def build_repetitions(batch_size):
    for threshold, repetitions in BUILD_REPETITIONS_SCHEDULE:
        if batch_size <= threshold:
            return repetitions
    return DEFAULT_BUILD_REPETITIONS

def build_subset(books, batch_size):
    subset = dict(list(books.items())[:batch_size])
    subset.update(synthetic_books(books, batch_size - len(subset)))
    return subset

def synthetic_books(books, count):
    corpus_tokens = list(books.values())
    return {
        SYNTHETIC_BOOK_ID_BASE + offset: corpus_tokens[offset % len(corpus_tokens)]
        for offset in range(count)
    }

def measure_query_performance(structure, queries):
    durations = []
    for _ in range(query_rounds(queries)):
        for terms in queries:
            start_time = time.perf_counter()
            matching_documents(structure, terms)
            durations.append(time.perf_counter() - start_time)
    stats = calculate_statistics(durations)
    stats["test_name"] = f"query_{structure.name}"
    save_statistics(stats)

def query_rounds(queries):
    return max(1, QUERY_SAMPLE_TARGET // len(queries))

def matching_documents(structure, terms):
    matched = set(structure.query_postings(terms[0]))
    for term in terms[1:]:
        matched &= set(structure.query_postings(term))
        if not matched:
            break
    return sorted(matched)

def load_shared_queries():
    return load_queries(QUERIES_PATH)

def measure_update(structure, books):
    new_book_id = max(books) + 1
    tokens = next(iter(books.values()))
    measurement = measure_operation(lambda: structure.add_book(new_book_id, tokens))
    save_result({
        "function_name": f"update_{structure.name}",
        "elapsed_seconds": measurement.elapsed_seconds,
        "memory_mb": measurement.memory_mb,
        "cpu_percent": measurement.cpu_percent,
    })

def measure_update_scaling(structure, books):
    """Isolates the incremental update cost: builds a base index of a given
    size (untimed), then times repeated single-book additions on top of it, so
    the report can show how each structure scales as the index grows."""
    tokens = next(iter(books.values()))
    for base_size in UPDATE_BASE_SIZES:
        structure.build_and_save(build_subset(books, base_size))
        samples = [
            measure_operation(
                lambda offset=offset: structure.add_book(
                    SYNTHETIC_BOOK_ID_BASE + base_size * 100 + offset, tokens))
            for offset in range(UPDATE_REPETITIONS)
        ]
        save_updates({
            "test_name": f"update_{structure.name}",
            "base_size": base_size,
            **aggregate_scalability(samples),
        })

def measure_storage_overhead(structure):
    save_disk_usage(structure.storage_usage())

def batch_sizes(book_count):
    return sorted({*BUILD_BATCH_SIZES, book_count})

def load_tokenized_books():
    bodies_directory = data_source.bodies_directory()
    book_ids = data_source.book_ids()
    return {book_id: process_text(read_book_body(book_id, bodies_directory)) for book_id in book_ids}

def create_mongo_structure():
    from src.datamarts.inverted_index import mongo_index
    if not mongo_index.is_available():
        raise ConnectionError("MongoDB server is not available")
    return MongoIndexStructure(mongo_index)

class JsonIndexStructure:
    name = "json_index"

    def reset(self):
        if JSON_INDEX_PATH.exists():
            JSON_INDEX_PATH.unlink()
        self.loaded = {}

    def build_and_save(self, books):
        json_index.save_index(json_index.build_index(books), JSON_INDEX_PATH)

    def prepare_query(self):
        self.loaded = json_index.load_index(JSON_INDEX_PATH)

    def query_postings(self, term):
        return self.loaded.get(term, [])

    def add_book(self, book_id, tokens):
        json_index.add_book(book_id, tokens, JSON_INDEX_PATH)

    def storage_usage(self):
        return measure_disk_usage(JSON_INDEX_PATH)

class FolderIndexStructure:
    name = "folder_index"

    def reset(self):
        if FOLDER_INDEX_PATH.exists():
            shutil.rmtree(FOLDER_INDEX_PATH)

    def build_and_save(self, books):
        folder_index.build_index(books, FOLDER_INDEX_PATH)

    def prepare_query(self):
        pass

    def query_postings(self, term):
        return folder_index.query_index(term, FOLDER_INDEX_PATH)

    def add_book(self, book_id, tokens):
        folder_index.update_book(book_id, tokens, FOLDER_INDEX_PATH)

    def storage_usage(self):
        return measure_disk_usage(FOLDER_INDEX_PATH)

class MongoIndexStructure:
    name = "mongo_index"

    def __init__(self, backend):
        self.backend = backend
        self.collection = backend.get_collection(database_name=BENCHMARK_MONGO_DATABASE)

    def reset(self):
        self.collection.delete_many({})

    def build_and_save(self, books):
        self.backend.save_index(self.backend.build_index(books), self.collection)

    def prepare_query(self):
        self.backend.is_available()

    def query_postings(self, term):
        return self.backend.query_index(term, self.collection)

    def add_book(self, book_id, tokens):
        self.backend.update_book(book_id, tokens, self.collection)

    def storage_usage(self):
        stats = self.collection.database.command("collStats", self.collection.name)
        host, port = self.collection.database.client.address
        return {
            "path": f"mongodb://{host}:{port}/{self.collection.database.name}.{self.collection.name}",
            "size_mb": round(stats["storageSize"] / BYTES_PER_MB, 4),
            "file_count": 0,
            "dir_count": 0,
        }

if __name__ == "__main__":
    configure_logging()
    run()
