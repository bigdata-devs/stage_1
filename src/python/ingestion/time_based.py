from pathlib import Path
from datetime import datetime
from src.python.ingestion.downloader import fetch_and_save, PROJECT_ROOT

def download_time_based(book_id: int, base_path: str = str(PROJECT_ROOT / "datalake")):
    now = datetime.now()
    output_path = Path(base_path) / now.strftime("%Y%m%d") / now.strftime("%H")
    return fetch_and_save(book_id, output_path)