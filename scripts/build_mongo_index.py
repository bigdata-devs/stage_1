import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.text_processor import process_text
from inverted_index.mongo_index import build_index, get_collection, save_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BODIES_DIR = Path(__file__).parent.parent / "sample_data" / "bodies"


def read_book_body(book_id: int, bodies_dir: Path) -> str:
    body_path = bodies_dir / f"{book_id}_body.txt"
    return body_path.read_text(encoding="utf-8")


def discover_book_ids(bodies_dir: Path) -> list[int]:
    book_ids = []
    for body_file in bodies_dir.glob("*_body.txt"):
        raw_id = body_file.stem.replace("_body", "")
        book_ids.append(int(raw_id))
    return sorted(book_ids)


def main() -> None:
    logger.info("Reading books from: %s", BODIES_DIR)
    book_ids = discover_book_ids(BODIES_DIR)
    logger.info("Found %d books: %s", len(book_ids), book_ids)

    books: dict[int, list[str]] = {}
    for book_id in book_ids:
        text = read_book_body(book_id, BODIES_DIR)
        tokens = process_text(text)
        books[book_id] = tokens
        logger.info("Book %d: %d tokens", book_id, len(tokens))

    logger.info("Building inverted index...")
    index = build_index(books)
    logger.info("Index contains %d unique terms", len(index))

    collection = get_collection()
    save_index(index, collection)
    logger.info(
        "Index saved to MongoDB collection: %s.%s",
        collection.database.name,
        collection.name,
    )


if __name__ == "__main__":
    main()
