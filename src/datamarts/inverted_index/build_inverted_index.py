"""Builds the monolithic JSON inverted index (``datamarts/inverted_index.json``) from the datalake.

Usage: python -m src.datamarts.inverted_index.build_inverted_index
"""

import logging

from src.datamarts.inverted_index.corpus import load_corpus
from src.datamarts.inverted_index.json_index import build_index, save_index
from src.datamarts.metadata.storage import SQLiteStorage
from src.utils.paths import JSON_INDEX_PATH

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    index = build_index(load_corpus(SQLiteStorage()))
    save_index(index, JSON_INDEX_PATH)
    logger.info("Index with %d unique terms saved to: %s", len(index), JSON_INDEX_PATH)


if __name__ == "__main__":
    main()
