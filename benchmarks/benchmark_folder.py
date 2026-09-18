import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from shared.text_processor import process_text
from inverted_index.folder_index import build_index, save_index, load_index, query_index
from benchmark_runner import (
    run_benchmark,
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


def benchmark_indexing_speed(books: dict, output_path: Path) -> dict:
    def build_with_cleanup():
        if output_path.exists():
            shutil.rmtree(output_path)
        build_index(books, output_path)

    return run_benchmark(build_with_cleanup, iterations=2)


def benchmark_query_performance(index_path: Path) -> dict:
    index = load_index(index_path)
    terms = list(index.keys())[:5]

    def run_queries():
        for term in terms:
            query_index(term, index_path)

    return run_benchmark(run_queries, iterations=100)


def benchmark_update_performance(index_path: Path) -> dict:
    new_book_tokens = ["new", "book", "tokens", "added", "here"]

    def update_index():
        for token in new_book_tokens:
            save_index({token: [99999]}, index_path)

    return run_benchmark(update_index, iterations=5)


def benchmark_disk_usage(index_path: Path) -> dict:
    total_files = sum(1 for _ in index_path.rglob("*.txt"))
    total_size = sum(f.stat().st_size for f in index_path.rglob("*.txt"))
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
    }


def main() -> None:
    book_ids = discover_book_ids(SAMPLE_BODIES)
    books = prepare_books(book_ids)

    index_path = RESULTS_DIR / "folder_index_benchmark"

    print(f"[INFO] Benchmarking with {len(book_ids)} books...")

    print("[INFO] Benchmarking indexing speed (this takes ~50s on Windows)...")
    indexing_speed = benchmark_indexing_speed(books, index_path)

    print("[INFO] Benchmarking query performance...")
    query_performance = benchmark_query_performance(index_path)

    print("[INFO] Benchmarking update performance...")
    update_performance = benchmark_update_performance(index_path)

    print("[INFO] Benchmarking disk usage...")
    disk_usage = benchmark_disk_usage(index_path)

    results = {
        "indexing_speed": indexing_speed,
        "query_performance": query_performance,
        "update_performance": update_performance,
        "disk_usage": disk_usage,
    }

    output_path = RESULTS_DIR / "benchmark_folder_results.json"
    save_results(results, output_path)
    print(f"[OK] Results saved to: {output_path}")

    print("\n=== Summary ===")
    print(f"Indexing speed: {indexing_speed['mean']:.4f}s (avg)")
    print(f"Query performance: {query_performance['mean']:.6f}s per query")
    print(f"Update performance: {update_performance['mean']:.4f}s")
    print(f"Disk usage: {disk_usage['total_files']} files, {disk_usage['total_size_bytes'] / 1024:.2f} KB")


if __name__ == "__main__":
    main()
