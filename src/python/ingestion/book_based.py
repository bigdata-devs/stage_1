from pathlib import Path
from src.python.ingestion.downloader import fetch_and_save, PROJECT_ROOT

def download_book_based(book_id: int, base_path: str = str(PROJECT_ROOT / "datalake")):
    output_path = Path(base_path) / str(book_id)
    return fetch_and_save(book_id, output_path)