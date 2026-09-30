import logging

from src.datamarts.metadata.storage import SQLiteStorage
from src.utils.benchmarks import data_source, datalake_experiments, metadata_experiments

logging.basicConfig(level=logging.INFO)

def main():
    data_source.prepare_books()
    logging.info("Populating benchmark datalake layouts")
    populate_datalake_layouts()
    logging.info("Writing frozen metadata database")
    save_frozen_metadata()
    logging.info("Frozen benchmark environment ready")

def populate_datalake_layouts():
    book_ids = data_source.book_ids()
    for layout in datalake_experiments.LAYOUTS:
        datalake_experiments.reset_structure_directory(layout)
        datalake_experiments.populate_structure(layout, book_ids)

def save_frozen_metadata():
    storage = SQLiteStorage()
    for metadata in metadata_experiments.load_book_metadata():
        storage.save(metadata)

if __name__ == "__main__":
    main()
