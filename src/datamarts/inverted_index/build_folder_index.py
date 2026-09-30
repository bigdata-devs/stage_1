"""Builds the hierarchical folder inverted index (``datamarts/inverted_index/<LETTER>/<term>.txt``) from the datalake.

Usage: python -m src.datamarts.inverted_index.build_folder_index
"""

import logging

from src.datamarts.inverted_index.corpus import load_corpus
from src.datamarts.inverted_index.folder_index import save_index
from src.datamarts.inverted_index.postings import build_postings
from src.datamarts.metadata.storage import SQLiteStorage
from src.utils.paths import FOLDER_INDEX_DIR

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    index = build_postings(load_corpus(SQLiteStorage()))
    save_index(index, FOLDER_INDEX_DIR)
    logger.info("Index with %d unique terms saved to: %s", len(index), FOLDER_INDEX_DIR)


if __name__ == "__main__":
    main()
