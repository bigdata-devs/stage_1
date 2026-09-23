from pathlib import Path
from src.python.ingestion.downloader import fetch_and_save, PROJECT_ROOT

def download_batch_based(book_id: int, base_path: str = str(PROJECT_ROOT / "datalake"), batch_size: int = 1000):
    rango_inferior = (book_id // batch_size) * batch_size
    rango_superior = rango_inferior + batch_size - 1
    output_path = Path(base_path) / f"batch_{rango_inferior}_{rango_superior}"
    return fetch_and_save(book_id, output_path)