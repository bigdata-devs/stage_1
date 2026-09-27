import requests
from pathlib import Path
from datetime import datetime

from src.utils.paths import PROJECT_ROOT

START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"

def download_time_based(book_id: int, base_path: str = str(PROJECT_ROOT / "datalake")):
    """
    Descarga un libro y lo guarda usando una jerarquía basada en el tiempo:
    datalake/YYYYMMDD/HH/<BOOK_ID>_body.txt
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    hour_str = now.strftime("%H")
    
    output_path = Path(base_path) / date_str / hour_str
    output_path.mkdir(parents=True, exist_ok=True)
    
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    print(f"Descargando libro {book_id} desde {url}...")
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error al descargar el libro {book_id}")
        return False
        
    text = response.text
    
    if START_MARKER not in text or END_MARKER not in text:
        print(f"El libro {book_id} no tiene el formato estándar.")
        return False
        
    header, body_and_footer = text.split(START_MARKER, 1)
    body, footer = body_and_footer.split(END_MARKER, 1)
    
    body_path = output_path / f"{book_id}_body.txt"
    header_path = output_path / f"{book_id}_header.txt"
    
    with open(body_path, "w", encoding="utf-8") as f:
        f.write(body.strip())
        
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(header.strip())
        
    print(f"Libro {book_id} guardado correctamente en {output_path}")
    return True



def download_book_based(book_id: int, base_path: str = "datalake"):
    """
    Guarda usando una jerarquía basada en el libro:
    datalake/<BOOK_ID>/<BOOK_ID>_body.txt
    """
    output_path = Path(base_path) / str(book_id)
    output_path.mkdir(parents=True, exist_ok=True)
    
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    response = requests.get(url)
    
    if response.status_code == 200 and START_MARKER in response.text:
        text = response.text
        header, body_and_footer = text.split(START_MARKER, 1)
        body, footer = body_and_footer.split(END_MARKER, 1)
        
        with open(output_path / f"{book_id}_body.txt", "w", encoding="utf-8") as f:
            f.write(body.strip())
        with open(output_path / f"{book_id}_header.txt", "w", encoding="utf-8") as f:
            f.write(header.strip())
            
        print(f"Libro {book_id} guardado (Book-based) en {output_path}")
        return True
    return False



def download_batch_based(book_id: int, base_path: str = "datalake", batch_size: int = 1000):
    """
    Guarda usando una jerarquía basada en lotes:
    datalake/batch_1000_1999/<BOOK_ID>_body.txt
    """
    rango_inferior = (book_id // batch_size) * batch_size
    rango_superior = rango_inferior + batch_size - 1
    
    carpeta_lote = f"batch_{rango_inferior}_{rango_superior}"
    output_path = Path(base_path) / carpeta_lote
    output_path.mkdir(parents=True, exist_ok=True)
    
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    response = requests.get(url)
    
    if response.status_code == 200 and START_MARKER in response.text:
        text = response.text
        header, body_and_footer = text.split(START_MARKER, 1)
        body, footer = body_and_footer.split(END_MARKER, 1)
        
        with open(output_path / f"{book_id}_body.txt", "w", encoding="utf-8") as f:
            f.write(body.strip())
        with open(output_path / f"{book_id}_header.txt", "w", encoding="utf-8") as f:
            f.write(header.strip())
            
        print(f"Libro {book_id} guardado (Batch-based) en {output_path}")
        return True
    return False



if __name__ == "__main__":
    print("--- Probando Time-based ---")
    download_time_based(1342)
    
    print("\n--- Probando Book-based ---")
    download_book_based(84)
    
    print("\n--- Probando Batch-based ---")
    download_batch_based(1500)
    download_batch_based(2500)
