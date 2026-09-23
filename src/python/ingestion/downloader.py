import requests
from pathlib import Path

START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def fetch_and_save(book_id: int, output_path: Path):
    """Descarga, divide y guarda el libro en la ruta proporcionada."""
    output_path.mkdir(parents=True, exist_ok=True)
    
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    print(f"Descargando libro {book_id} desde {url}...")
    
    response = requests.get(url)
    if response.status_code != 200 or START_MARKER not in response.text:
        print(f"Error o formato inválido para el libro {book_id}")
        return False
        
    text = response.text
    header, body_and_footer = text.split(START_MARKER, 1)
    body, footer = body_and_footer.split(END_MARKER, 1)
    
    with open(output_path / f"{book_id}_body.txt", "w", encoding="utf-8") as f:
        f.write(body.strip())
    with open(output_path / f"{book_id}_header.txt", "w", encoding="utf-8") as f:
        f.write(header.strip())
        
    print(f"Libro {book_id} guardado correctamente en {output_path}")
    return True