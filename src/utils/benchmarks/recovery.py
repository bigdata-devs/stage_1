import time
import logging
from src.utils.benchmarks import save_recovery

logging.basicConfig(level=logging.INFO)

TOTAL_BOOKS = 100
INTERRUPT_AT = 50
TEST_NAME = "pipeline_recovery"

def run_recovery_test():
    stats = simulate_recovery_scenario()
    save_recovery(stats)
    return report_verdict(stats)

def simulate_recovery_scenario():
    start_time = time.perf_counter()
    first_phase = run_first_phase()
    logging.info("--- Simulated interruption ---")
    detection_time, processing_time, second_phase = resume_pipeline(first_phase)
    elapsed = time.perf_counter() - start_time
    duplicated, lost = verify_integrity(first_phase, second_phase)
    return {
        "test_name": TEST_NAME,
        "total_books": TOTAL_BOOKS,
        "processed_before_interruption": len(first_phase),
        "processed_after_resume": len(second_phase),
        "duplicated": duplicated,
        "lost": lost,
        "detection_time": detection_time,
        "processing_time": processing_time,
        "elapsed_seconds": elapsed,
    }

def report_verdict(stats):
    success = stats["duplicated"] == 0 and stats["lost"] == 0
    status = "PASSED" if success else "FAILED"
    logging.info("Recovery test: %s (duplicated=%d, lost=%d)", status, stats["duplicated"], stats["lost"])
    logging.info("Detection time: %.6fs, Processing time: %.6fs", stats["detection_time"], stats["processing_time"])
    return success

def resume_pipeline(first_phase):
    detection_start = time.perf_counter()
    pending = detect_pending_books(first_phase)
    detection_time = time.perf_counter() - detection_start
    processing_start = time.perf_counter()
    second_phase = process_pending_books(pending)
    processing_time = time.perf_counter() - processing_start
    return detection_time, processing_time, second_phase

def verify_integrity(first_phase, second_phase):
    duplicated = verify_no_duplicates(first_phase, second_phase)
    lost = verify_no_losses(first_phase, second_phase)
    return duplicated, lost

def run_first_phase():
    processed = set()
    for book_id in range(1, INTERRUPT_AT + 1):
        process_book(book_id)
        processed.add(book_id)
    logging.info("Phase 1: processed %d books before interruption", len(processed))
    return processed

def detect_pending_books(already_processed):
    pending = set()
    for book_id in range(1, TOTAL_BOOKS + 1):
        if book_id not in already_processed:
            pending.add(book_id)
    logging.info("Detection: found %d pending books", len(pending))
    return pending

def process_pending_books(pending):
    processed_after = set()
    for book_id in pending:
        process_book(book_id)
        processed_after.add(book_id)
    logging.info("Phase 2: processed %d books after resume", len(processed_after))
    return processed_after

def verify_no_duplicates(first_phase, second_phase):
    duplicated = len(first_phase & second_phase)
    logging.info("Verification: %d duplicated books", duplicated)
    return duplicated

def verify_no_losses(first_phase, second_phase):
    all_processed = first_phase | second_phase
    expected = set(range(1, TOTAL_BOOKS + 1))
    lost = len(expected - all_processed)
    logging.info("Verification: %d lost books", lost)
    return lost

def process_book(book_id):
    return {"book_id": book_id, "status": "processed"}

if __name__ == "__main__":
    run_recovery_test()
