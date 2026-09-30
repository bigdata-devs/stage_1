import time
import shutil
import logging
from pathlib import Path
from collections import Counter

from src.utils.benchmarks import (
    BYTES_PER_MB,
    measure_operation,
    calculate_throughput,
    calculate_statistics,
    save_throughput,
    save_result,
    save_statistics,
    save_scalability,
    save_disk_usage,
)
from src.utils.benchmarks import data_source
from src.utils.benchmarks.artifacts import ARTIFACT_ROOT
from src.datamarts.metadata.header_parser import extract_metadata
from src.utils.benchmarks.storage import SQLiteStorage, PostgresStorage, MongoStorage

logging.basicConfig(level=logging.INFO)

METADATA_DIRECTORY = ARTIFACT_ROOT / "metadata"
DATABASE_PATH = METADATA_DIRECTORY / "metadata.db"
MONGO_CONNECTION_STRING = "mongodb://localhost:27017/?serverSelectionTimeoutMS=1000"
POSTGRES_CONNECTION_STRING = "host=/var/run/postgresql dbname=bigdata"
QUERY_ITERATIONS = 100
SCALABILITY_BATCH_SIZES = [10, 100, 1000, 10000]
SYNTHETIC_BOOK_ID_BASE = 900000
STORAGE_FILE_COUNTS = {"sqlite": 1, "postgres": 0, "mongo": 0}

def run():
    reset_database()
    metadata_rows = load_book_metadata()
    logging.info("Loaded metadata for %s books", len(metadata_rows))
    skipped = []
    creators = [
        ("sqlite", create_sqlite_storage),
        ("postgres", create_postgres_storage),
        ("mongo", create_mongo_storage),
    ]
    for name, creator in creators:
        skipped.extend(run_backend_experiments(name, creator, metadata_rows))
    return skipped

def run_backend_experiments(name, creator, metadata_rows):
    try:
        storage = creator()
    except (ImportError, ConnectionError) as error:
        logging.warning("SKIP %s metadata storage: %s", name, error)
        return [name]
    run_storage_experiments(storage, name, metadata_rows)
    return []

def reset_database():
    shutil.rmtree(METADATA_DIRECTORY, ignore_errors=True)

def load_book_metadata():
    headers_directory = data_source.headers_directory()
    metadata_rows = []
    for book_id in data_source.book_ids():
        header_text = read_header(book_id, headers_directory)
        metadata_rows.append({"book_id": book_id, **extract_metadata(header_text)})
    return metadata_rows

def read_header(book_id, headers_directory):
    header_path = headers_directory / f"{book_id}_header.txt"
    return header_path.read_text(encoding="utf-8", errors="replace")

def create_sqlite_storage():
    METADATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return SQLiteStorage(db_path=str(DATABASE_PATH))

def create_postgres_storage():
    return PostgresStorage(POSTGRES_CONNECTION_STRING)

def create_mongo_storage():
    storage = MongoStorage(MONGO_CONNECTION_STRING)
    probe_mongo_connection(storage)
    return storage

def probe_mongo_connection(storage):
    from pymongo.errors import ServerSelectionTimeoutError
    try:
        storage.client.admin.command("ping")
    except ServerSelectionTimeoutError as error:
        raise ConnectionError("MongoDB server is not available") from error

def run_storage_experiments(storage, name, metadata_rows):
    logging.info("--- Metadata storage: %s ---", name)
    measure_insert_throughput(storage, metadata_rows, name)
    measure_queries(storage, name, metadata_rows)
    measure_insert_scalability(storage, metadata_rows[0], name)
    measure_storage_overhead(storage, name)

def measure_storage_overhead(storage, name):
    save_disk_usage({
        "path": storage.storage_location(),
        "size_mb": round(storage.storage_size_bytes() / BYTES_PER_MB, 4),
        "file_count": STORAGE_FILE_COUNTS[name],
        "dir_count": 0,
    })

def measure_insert_throughput(storage, metadata_rows, name):
    measurement = measure_operation(lambda: save_all(storage, metadata_rows))
    save_throughput({
        "test_name": f"insert_throughput_{name}",
        "item_count": len(metadata_rows),
        "elapsed_seconds": measurement.elapsed_seconds,
        "items_per_second": calculate_throughput(len(metadata_rows), measurement.elapsed_seconds),
    })
    save_result({
        "function_name": f"insert_{name}",
        "elapsed_seconds": measurement.elapsed_seconds,
        "memory_mb": measurement.memory_mb,
        "cpu_percent": measurement.cpu_percent,
    })

def measure_queries(storage, name, metadata_rows):
    author = most_common_author(metadata_rows)
    first_book_id = metadata_rows[0]["book_id"]
    measure_query_performance(f"query_author_{name}", lambda: storage.find_by_author(author))
    measure_query_performance(f"query_id_{name}", lambda: storage.find_by_book_id(first_book_id))

def most_common_author(metadata_rows):
    author_counts = Counter(row["Author"] for row in metadata_rows)
    return author_counts.most_common(1)[0][0]

def measure_query_performance(test_name, query):
    durations = []
    for _ in range(QUERY_ITERATIONS):
        start_time = time.perf_counter()
        query()
        durations.append(time.perf_counter() - start_time)
    stats = calculate_statistics(durations)
    stats["test_name"] = test_name
    save_statistics(stats)

def measure_insert_scalability(storage, template, name):
    for batch_size in SCALABILITY_BATCH_SIZES:
        rows = synthetic_metadata_rows(batch_size, template)
        measurement = measure_operation(lambda: save_all(storage, rows))
        save_scalability({
            "test_name": f"insert_{name}",
            "batch_size": batch_size,
            "elapsed_seconds": measurement.elapsed_seconds,
            "memory_mb": measurement.memory_mb,
            "cpu_percent": measurement.cpu_percent,
        })

def synthetic_metadata_rows(count, template):
    return [dict(template, book_id=SYNTHETIC_BOOK_ID_BASE + offset) for offset in range(count)]

def save_all(storage, metadata_rows):
    for metadata in metadata_rows:
        storage.save(metadata)

if __name__ == "__main__":
    run()
