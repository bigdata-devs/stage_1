import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from shared.text_processor import process_text
from inverted_index.mongo_index import (
    DEFAULT_MONGO_URI,
    build_index,
    get_collection,
    is_available,
    query_index,
    save_index,
    update_book,
)
from benchmark_runner import (
    run_benchmark,
    measure_memory,
    save_results,
)

SAMPLE_BODIES = Path(__file__).parent.parent / "sample_data" / "bodies"
RESULTS_DIR = Path(__file__).parent / "results"
BENCHMARK_COLLECTION_NAME = "inverted_index_benchmark"


def discover_book_ids(bodies_dir: Path) -> list[int]:
    book_ids = []
    for body_file in bodies_dir.glob("*_body.txt"):
        raw_id = body_file.stem.replace("_body", "")
        book_ids.append(int(raw_id))
    return sorted(book_ids)


def read_book_body(book_id: int, bodies_dir: Path) -> str:
    body_path = bodies_dir / f"{book_id}_body.txt"
    return body_path.read_text(encoding="utf-8")


def prepare_books(book_ids: list[int]) -> dict[int, list[str]]:
    books = {}
    for book_id in book_ids:
        text = read_book_body(book_id, SAMPLE_BODIES)
        books[book_id] = process_text(text)
    return books


def benchmark_indexing_speed(books: dict, collection) -> dict:
    def build_with_cleanup():
        index = build_index(books)
        save_index(index, collection)

    return run_benchmark(build_with_cleanup, iterations=5)


def benchmark_query_performance(collection) -> dict:
    common_words = ["adventure", "pride", "prejudice", "island", "shipwreck"]
    rare_words = ["wonderland", "mockturtle"]

    def run_queries():
        for word in common_words + rare_words:
            query_index(word, collection)

    return run_benchmark(run_queries, iterations=1000)


def benchmark_update_performance(collection) -> dict:
    new_book_tokens = ["new", "book", "tokens", "added", "here"]

    def update_index():
        update_book(99999, new_book_tokens, collection)

    return run_benchmark(update_index, iterations=10)


def benchmark_memory_usage(books: dict) -> dict:
    _, peak_memory = measure_memory(build_index, books=books)
    return {"peak_memory_bytes": peak_memory}


def benchmark_disk_usage(collection) -> dict:
    stats = collection.database.command("dbstats")
    index_stats = collection.database.command("collStats", collection.name)
    return {
        "storage_size_bytes": stats.get("storageSize", 0),
        "data_size_bytes": stats.get("dataSize", 0),
        "index_size_bytes": index_stats.get("totalIndexSize", 0),
    }


def benchmark_scalability(collection) -> dict:
    book_ids = discover_book_ids(SAMPLE_BODIES)
    results = {}

    for num_books in range(1, len(book_ids) + 1):
        subset = book_ids[:num_books]
        books = prepare_books(subset)

        def build_subset():
            save_index(build_index(books), collection)

        stats = run_benchmark(build_subset, iterations=3)
        results[num_books] = {
            "num_books": num_books,
            "indexing_time": stats["mean"],
        }

    return results


def main() -> None:
    if not is_available(DEFAULT_MONGO_URI):
        print("[ERROR] MongoDB is not available. Start it with: docker compose up -d")
        return

    book_ids = discover_book_ids(SAMPLE_BODIES)
    books = prepare_books(book_ids)
    collection = get_collection(
        DEFAULT_MONGO_URI,
        "search_engine_benchmark",
        BENCHMARK_COLLECTION_NAME,
    )
    save_index(build_index(books), collection)

    print(f"[INFO] Benchmarking with {len(book_ids)} books...")
    print(f"[INFO] Index contains {collection.count_documents({})} unique terms")

    print("[INFO] Benchmarking indexing speed...")
    indexing_speed = benchmark_indexing_speed(books, collection)

    print("[INFO] Benchmarking query performance...")
    query_performance = benchmark_query_performance(collection)

    print("[INFO] Benchmarking update performance...")
    update_performance = benchmark_update_performance(collection)

    print("[INFO] Benchmarking memory usage...")
    memory_usage = benchmark_memory_usage(books)

    print("[INFO] Benchmarking disk usage...")
    disk_usage = benchmark_disk_usage(collection)

    print("[INFO] Benchmarking scalability...")
    scalability = benchmark_scalability(collection)

    results = {
        "indexing_speed": indexing_speed,
        "query_performance": query_performance,
        "update_performance": update_performance,
        "memory_usage": memory_usage,
        "disk_usage": disk_usage,
        "scalability": scalability,
    }

    output_path = RESULTS_DIR / "benchmark_mongo_results.json"
    save_results(results, output_path)
    collection.database.command("dropDatabase")
    print(f"[OK] Results saved to: {output_path}")

    print("\n=== Summary ===")
    print(f"Indexing speed: {indexing_speed['mean']:.4f}s (avg)")
    print(f"Query performance: {query_performance['mean']:.6f}s per query")
    print(f"Update performance: {update_performance['mean']:.4f}s")
    print(f"Memory usage: {memory_usage['peak_memory_bytes'] / 1024:.2f} KB")
    print(
        f"Disk usage: {disk_usage['storage_size_bytes'] / 1024:.2f} KB "
        f"(index: {disk_usage['index_size_bytes'] / 1024:.2f} KB)"
    )


if __name__ == "__main__":
    main()
