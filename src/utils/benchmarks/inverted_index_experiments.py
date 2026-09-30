import logging
import random
import shutil
import time
from pathlib import Path

from src.utils.benchmarks import (
    BYTES_PER_MB,
    measure_operation,
    measure_disk_usage,
    calculate_statistics,
    save_scalability,
    save_result,
    save_statistics,
    save_disk_usage,
)
from src.utils.benchmarks import data_source
from src.utils.benchmarks.artifacts import ARTIFACT_ROOT
from src.utils.body_files import read_book_body
from src.utils.text_processor import process_text
from src.datamarts.inverted_index import json_index, folder_index

logging.basicConfig(level=logging.INFO)

INDEX_OUTPUT_DIRECTORY = ARTIFACT_ROOT / "index"
JSON_INDEX_PATH = INDEX_OUTPUT_DIRECTORY / "inverted_index.json"
FOLDER_INDEX_PATH = INDEX_OUTPUT_DIRECTORY / "inverted_index"
BUILD_BATCH_SIZES = (10, 25, 50)
QUERY_SAMPLE_SIZE = 100
RANDOM_SEED = 42

def run():
    books = load_tokenized_books()
    logging.info("Loaded %s books for the index experiments", len(books))
    terms = corpus_terms(books)
    structures = [JsonIndexStructure(), FolderIndexStructure()]
    skipped = []
    try:
        structures.append(create_mongo_structure())
    except (ImportError, ConnectionError) as error:
        logging.warning("SKIP mongo_index: %s", error)
        skipped.append("mongo_index")
    for structure in structures:
        run_structure_experiments(structure, books, terms)
    return skipped

def run_structure_experiments(structure, books, terms):
    logging.info("--- Inverted index structure: %s ---", structure.name)
    structure.reset()
    for batch_size in batch_sizes(len(books)):
        measure_build(structure, books, batch_size)
    structure.prepare_query()
    measure_query_performance(structure, select_query_terms(terms))
    measure_update(structure, books)
    measure_storage_overhead(structure)

def measure_build(structure, books, batch_size):
    subset = dict(list(books.items())[:batch_size])
    measurement = measure_operation(lambda: structure.build_and_save(subset))
    save_scalability({
        "test_name": f"build_{structure.name}",
        "batch_size": batch_size,
        "elapsed_seconds": measurement.elapsed_seconds,
        "memory_mb": measurement.memory_mb,
        "cpu_percent": measurement.cpu_percent,
    })

def measure_query_performance(structure, terms):
    durations = []
    for term in terms:
        start_time = time.perf_counter()
        structure.query_postings(term)
        durations.append(time.perf_counter() - start_time)
    stats = calculate_statistics(durations)
    stats["test_name"] = f"query_{structure.name}"
    save_statistics(stats)

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

def measure_storage_overhead(structure):
    save_disk_usage(structure.storage_usage())

def select_query_terms(terms):
    generator = random.Random(RANDOM_SEED)
    return generator.sample(sorted(terms), min(QUERY_SAMPLE_SIZE, len(terms)))

def batch_sizes(book_count):
    sizes = {size for size in BUILD_BATCH_SIZES if size <= book_count}
    sizes.add(book_count)
    return sorted(sizes)

def load_tokenized_books():
    bodies_directory = data_source.bodies_directory()
    book_ids = data_source.book_ids()
    return {book_id: process_text(read_book_body(book_id, bodies_directory)) for book_id in book_ids}

def corpus_terms(books):
    terms = set()
    for tokens in books.values():
        terms.update(tokens)
    return sorted(terms)

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
        index = json_index.load_index(JSON_INDEX_PATH)
        for term in set(tokens):
            postings = index.setdefault(term, [])
            postings.append(book_id)
            postings.sort()
        json_index.save_index(index, JSON_INDEX_PATH)

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
        for term in set(tokens):
            append_to_term_file(term, book_id)

    def storage_usage(self):
        return measure_disk_usage(FOLDER_INDEX_PATH)

class MongoIndexStructure:
    name = "mongo_index"

    def __init__(self, backend):
        self.backend = backend
        self.collection = backend.get_collection()

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

def append_to_term_file(term, book_id):
    existing_ids = folder_index.query_index(term, FOLDER_INDEX_PATH)
    existing_ids.append(book_id)
    term_file = term_file_path(term)
    term_file.parent.mkdir(parents=True, exist_ok=True)
    ordered_ids = sorted(existing_ids)
    term_file.write_text("\n".join(str(entry) for entry in ordered_ids) + "\n", encoding="utf-8")

def term_file_path(term):
    return FOLDER_INDEX_PATH / term[0].upper() / f"{term}.txt"

if __name__ == "__main__":
    run()
