import logging
from src.utils.benchmarks import measure_operation, save_scalability

logging.basicConfig(level=logging.INFO)

BATCH_SIZES = [10, 50, 100, 500]
TEST_NAME = "mock_indexing"

def run_scalability_test():
    for batch_size in BATCH_SIZES:
        logging.info("--- Running test with batch_size=%d ---", batch_size)
        stats = measure_batch(batch_size)
        save_scalability(stats)
    logging.info("Scalability test '%s' completed. Results saved to scalability.csv", TEST_NAME)

def measure_batch(batch_size):
    measurement = measure_operation(lambda: mock_indexing(batch_size))
    return {
        "test_name": TEST_NAME,
        "batch_size": batch_size,
        "elapsed_seconds": measurement.elapsed_seconds,
        "memory_mb": measurement.memory_mb,
        "cpu_percent": measurement.cpu_percent,
    }

def mock_indexing(batch_size):
    inverted_index = {}
    for i in range(batch_size):
        book_id = i + 1
        words = [f"word_{book_id}_{j}" for j in range(100)]
        for word in words:
            if word not in inverted_index:
                inverted_index[word] = []
            inverted_index[word].append(book_id)
    return inverted_index

if __name__ == "__main__":
    run_scalability_test()
