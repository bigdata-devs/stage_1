import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from shared.text_processor import process_text
from inverted_index.json_index import build_index, save_index, load_index
from benchmark_runner import (
    run_benchmark,
    measure_memory,
    measure_disk_usage,
    save_results,
)

SAMPLE_BODIES = Path(__file__).parent.parent / "sample_data" / "bodies"
RESULTS_DIR = Path(__file__).parent / "results"


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


def benchmark_indexing_speed(books: dict) -> dict:
    return run_benchmark(build_index, iterations=5, books=books)


def benchmark_query_performance(index: dict) -> dict:
    common_words = ["adventure", "pride", "prejudice", "island", "shipwreck"]
    rare_words = ["wonderland", "mockturtle"]

    def run_queries():
        for word in common_words + rare_words:
            _ = index.get(word, [])

    return run_benchmark(run_queries, iterations=1000)


def benchmark_update_performance(index: dict) -> dict:
    new_book_tokens = ["new", "book", "tokens", "added", "here"]

    def update_index():
        updated = index.copy()
        for token in new_book_tokens:
            if token not in updated:
                updated[token] = []
            updated[token].append(99999)

    return run_benchmark(update_index, iterations=10)


def benchmark_memory_usage(books: dict) -> dict:
    _, peak_memory = measure_memory(build_index, books=books)
    return {"peak_memory_bytes": peak_memory}


def benchmark_disk_usage(index: dict, tmp_path: Path) -> dict:
    index_path = tmp_path / "benchmark_index.json"
    save_index(index, index_path)
    disk_bytes = measure_disk_usage(index_path)
    return {"disk_usage_bytes": disk_bytes}


def benchmark_scalability() -> dict:
    book_ids = discover_book_ids(SAMPLE_BODIES)
    results = {}

    for num_books in range(1, len(book_ids) + 1):
        subset = book_ids[:num_books]
        books = prepare_books(subset)
        stats = run_benchmark(build_index, iterations=3, books=books)
        results[num_books] = {
            "num_books": num_books,
            "indexing_time": stats["mean"],
        }

    return results


def main() -> None:
    book_ids = discover_book_ids(SAMPLE_BODIES)
    books = prepare_books(book_ids)
    index = build_index(books)

    print(f"[INFO] Benchmarking with {len(book_ids)} books...")
    print(f"[INFO] Index contains {len(index)} unique terms")

    print("[INFO] Benchmarking indexing speed...")
    indexing_speed = benchmark_indexing_speed(books)

    print("[INFO] Benchmarking query performance...")
    query_performance = benchmark_query_performance(index)

    print("[INFO] Benchmarking update performance...")
    update_performance = benchmark_update_performance(index)

    print("[INFO] Benchmarking memory usage...")
    memory_usage = benchmark_memory_usage(books)

    print("[INFO] Benchmarking disk usage...")
    disk_usage = benchmark_disk_usage(index, RESULTS_DIR)

    print("[INFO] Benchmarking scalability...")
    scalability = benchmark_scalability()

    results = {
        "indexing_speed": indexing_speed,
        "query_performance": query_performance,
        "update_performance": update_performance,
        "memory_usage": memory_usage,
        "disk_usage": disk_usage,
        "scalability": scalability,
    }

    output_path = RESULTS_DIR / "benchmark_json_results.json"
    save_results(results, output_path)
    print(f"[OK] Results saved to: {output_path}")

    print("\n=== Summary ===")
    print(f"Indexing speed: {indexing_speed['mean']:.4f}s (avg)")
    print(f"Query performance: {query_performance['mean']:.6f}s per query")
    print(f"Update performance: {update_performance['mean']:.4f}s")
    print(f"Memory usage: {memory_usage['peak_memory_bytes'] / 1024:.2f} KB")
    print(f"Disk usage: {disk_usage['disk_usage_bytes'] / 1024:.2f} KB")


if __name__ == "__main__":
    main()
