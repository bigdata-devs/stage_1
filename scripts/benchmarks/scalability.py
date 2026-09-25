import logging
from benchmarks import measure_time, measure_memory, measure_cpu_usage, save_scalability

logging.basicConfig(level=logging.INFO)

BATCH_SIZES = [10, 50, 100, 500]
TEST_NAME = "mock_indexing"

def run_scalability_test():
    for batch_size in BATCH_SIZES:
        logging.info(f"--- Running test with batch_size={batch_size} ---")
        stats = measure_batch(batch_size)
        save_scalability(stats)
    logging.info(f"Scalability test '{TEST_NAME}' completed. Results saved to scalability.csv")

def measure_batch(batch_size):
    time_func = measure_time(mock_indexing)
    memory_func = measure_memory(time_func)
    cpu_func = measure_cpu_usage(memory_func)
    cpu_func(batch_size)
    return {
        "test_name": TEST_NAME,
        "batch_size": batch_size,
        "elapsed_seconds": time_func.last_elapsed,
        "memory_mb": memory_func.last_memory_mb,
        "cpu_percent": cpu_func.last_cpu_percent,
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
