import time
import logging
from benchmarks import save_recovery

logging.basicConfig(level=logging.INFO)

TOTAL_BOOKS = 100
INTERRUPT_AT = 50
TEST_NAME = "pipeline_recovery"


def process_book(book_id):
    return {"book_id": book_id, "status": "processed"}


def run_first_phase():
    processed = set()
    for book_id in range(1, INTERRUPT_AT + 1):
        process_book(book_id)
        processed.add(book_id)
    logging.info(f"Phase 1: processed {len(processed)} books before interruption")
    return processed


def detect_pending_books(already_processed):
    pending = set()
    for book_id in range(1, TOTAL_BOOKS + 1):
        if book_id not in already_processed:
            pending.add(book_id)
    logging.info(f"Detection: found {len(pending)} pending books")
    return pending


def process_pending_books(pending):
    processed_after = set()
    for book_id in pending:
        process_book(book_id)
        processed_after.add(book_id)
    logging.info(f"Phase 2: processed {len(processed_after)} books after resume")
    return processed_after


def verify_no_duplicates(first_phase, second_phase):
    duplicated = len(first_phase & second_phase)
    logging.info(f"Verification: {duplicated} duplicated books")
    return duplicated


def verify_no_losses(first_phase, second_phase):
    all_processed = first_phase | second_phase
    expected = set(range(1, TOTAL_BOOKS + 1))
    lost = len(expected - all_processed)
    logging.info(f"Verification: {lost} lost books")
    return lost


def run_recovery_test():
    start_time = time.perf_counter()

    first_phase = run_first_phase()
    logging.info("--- Simulated interruption ---")

    detection_start = time.perf_counter()
    pending = detect_pending_books(first_phase)
    detection_time = time.perf_counter() - detection_start

    processing_start = time.perf_counter()
    second_phase = process_pending_books(pending)
    processing_time = time.perf_counter() - processing_start

    elapsed = time.perf_counter() - start_time

    duplicated = verify_no_duplicates(first_phase, second_phase)
    lost = verify_no_losses(first_phase, second_phase)

    save_recovery(
        TEST_NAME,
        TOTAL_BOOKS,
        len(first_phase),
        len(second_phase),
        duplicated,
        lost,
        detection_time,
        processing_time,
        elapsed,
    )

    success = duplicated == 0 and lost == 0
    status = "PASSED" if success else "FAILED"
    logging.info(f"Recovery test: {status} (duplicated={duplicated}, lost={lost})")
    logging.info(f"Detection time: {detection_time:.6f}s, Processing time: {processing_time:.6f}s")
    return success


if __name__ == "__main__":
    run_recovery_test()
