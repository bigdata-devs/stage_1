import logging

from src.datamarts.metadata.storage import SQLiteStorage
from src.utils.benchmarks import data_source, datalake_experiments, metadata_experiments
from src.utils.benchmarks.artifacts import METADATA_BENCHMARK_DB_PATH
from src.utils.benchmarks.logging_setup import configure_logging

def main():
    data_source.prepare_books()
    logging.info("Populating benchmark datalake layouts")
    populate_datalake_layouts()
    logging.info("Writing frozen metadata database to %s", METADATA_BENCHMARK_DB_PATH)
    save_frozen_metadata()
    logging.info("Frozen benchmark environment ready")

def populate_datalake_layouts():
    book_ids = data_source.book_ids()
    for layout in datalake_experiments.LAYOUTS:
        datalake_experiments.reset_structure_directory(layout)
        datalake_experiments.populate_structure(layout, book_ids)

def save_frozen_metadata():
    SQLiteStorage(METADATA_BENCHMARK_DB_PATH).save_many(metadata_experiments.load_book_metadata())

if __name__ == "__main__":
    configure_logging()
    main()
