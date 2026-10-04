"""Builds the MongoDB inverted index (``search_engine.inverted_index``) from the datalake.

Usage: python -m src.datamarts.inverted_index.build_mongo_index  (needs ``docker compose up -d``)
"""

import logging

from src.datamarts.inverted_index.corpus import load_corpus
from src.datamarts.inverted_index.mongo_index import build_index, get_collection, save_index
from src.datamarts.metadata.storage import SQLiteStorage

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    index = build_index(load_corpus(SQLiteStorage()))
    collection = get_collection()
    save_index(index, collection)
    logger.info("Index with %d unique terms saved to MongoDB collection: %s.%s",
                len(index), collection.database.name, collection.name)


if __name__ == "__main__":
    main()
