import json
import logging
import requests
from datetime import datetime
from pathlib import Path

from src.datalake.book_fetcher import END_MARKER, START_MARKER
from src.utils.body_files import discover_book_ids

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIRECTORY = PROJECT_ROOT / "data_source"
CACHED_BODIES_DIRECTORY = DATA_DIRECTORY / "bodies"
CACHED_HEADERS_DIRECTORY = DATA_DIRECTORY / "headers"
MANIFEST_PATH = DATA_DIRECTORY / "manifest.json"
SAMPLE_BODIES_DIRECTORY = PROJECT_ROOT / "sample_data" / "bodies"
SAMPLE_HEADERS_DIRECTORY = PROJECT_ROOT / "sample_data" / "headers"
GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
FAMOUS_BOOK_IDS = [1342, 11, 84, 174, 2701, 1661, 98, 1080, 1727, 43, 46, 1260, 345, 74, 205, 1497, 1232, 55, 120, 135]
TARGET_BOOK_COUNT = 100
MIN_BOOK_COUNT = 20
REQUEST_TIMEOUT_SECONDS = 30

def prepare_books():
    if MANIFEST_PATH.exists():
        logging.info("Books already prepared in %s", DATA_DIRECTORY)
        return
    download_books()
    if cached_book_count() >= MIN_BOOK_COUNT:
        write_manifest()
    else:
        logging.warning("Only %s books cached; experiments will use sample_data instead", cached_book_count())

def download_books():
    CACHED_BODIES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    CACHED_HEADERS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for book_id in candidate_ids():
        if downloaded >= TARGET_BOOK_COUNT:
            break
        try:
            cache_book(book_id)
        except requests.HTTPError:
            continue
        except requests.RequestException:
            logging.warning("Network unavailable; stopping the download after %s books", downloaded)
            break
        except ValueError:
            continue
        downloaded += 1
    logging.info("Cached %s books from Project Gutenberg", downloaded)

def cache_book(book_id):
    response = requests.get(GUTENBERG_URL.format(book_id=book_id), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    header, body = split_book(response.text)
    write_book_files(book_id, header, body)

def split_book(raw_text):
    if START_MARKER not in raw_text or END_MARKER not in raw_text:
        raise ValueError("Book text does not contain the Gutenberg markers")
    header, remainder = raw_text.split(START_MARKER, 1)
    body = remainder.split(END_MARKER, 1)[0]
    return header.strip(), body.strip()

def write_book_files(book_id, header, body):
    header_path = CACHED_HEADERS_DIRECTORY / f"{book_id}_header.txt"
    body_path = CACHED_BODIES_DIRECTORY / f"{book_id}_body.txt"
    header_path.write_text(header, encoding="utf-8")
    body_path.write_text(body, encoding="utf-8")

def candidate_ids():
    return list(dict.fromkeys([*FAMOUS_BOOK_IDS, *range(1, 601)]))

def cached_book_count():
    return len(discover_book_ids(CACHED_BODIES_DIRECTORY))

def write_manifest():
    manifest = {"created_at": datetime.now().isoformat(), "book_ids": discover_book_ids(CACHED_BODIES_DIRECTORY)}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def book_ids():
    return discover_book_ids(bodies_directory())

def bodies_directory():
    return CACHED_BODIES_DIRECTORY if using_cached_books() else SAMPLE_BODIES_DIRECTORY

def headers_directory():
    return CACHED_HEADERS_DIRECTORY if using_cached_books() else SAMPLE_HEADERS_DIRECTORY

def using_cached_books():
    return CACHED_BODIES_DIRECTORY.exists() and any(CACHED_BODIES_DIRECTORY.iterdir())
