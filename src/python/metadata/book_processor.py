import requests
import re
import os
from pathlib import Path
from storage import SQLiteStorage, PostgresStorage, MongoStorage
from datetime import datetime      

START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"

def extract_metadata(header_text: str) -> dict:
    """Extrae Título, Autor e Idioma de la cabecera usando expresiones regulares."""
    
    metadata = {
        "Title": "Unknown",
        "Author": "Unknown",
        "Language": "Unknown"
    }
    
    # Expresiones regulares para buscar los campos descriptivos
    title_match = re.search(r"Title:\s*(.+)", header_text, re.IGNORECASE)
    author_match = re.search(r"Author:\s*(.+)", header_text, re.IGNORECASE)
    language_match = re.search(r"Language:\s*(.+)", header_text, re.IGNORECASE)
    
    if title_match:
        metadata["Title"] = title_match.group(1).strip()
    if author_match:
        metadata["Author"] = author_match.group(1).strip()
    if language_match:
        metadata["Language"] = language_match.group(1).strip()
        
    return metadata

def process_book(book_id: int, output_dir: str, db_backend):
    """Descarga el libro, lo divide en partes y devuelve los metadatos."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Descargar el libro
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error descargando el libro {book_id}: {e}")
        return None
        
    text = response.text
    
    if START_MARKER not in text or END_MARKER not in text:
        print(f"Marcadores no encontrados en el libro {book_id}.")
        return None
        
    # Dividir el texto aislando cabecera, cuerpo y pie de página
    header, body_and_footer = text.split(START_MARKER, 1)
    body, footer = body_and_footer.split(END_MARKER, 1)
    
    # Guardar los archivos de texto limpio
    body_path = output_path / f"{book_id}_body.txt"
    header_path = output_path / f"{book_id}_header.txt"
    
    with open(body_path, "w", encoding="utf-8") as f:
        f.write(body.strip())
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(header.strip())
        
    # Extraer metadatos de la cabecera
    metadata = extract_metadata(header)
    metadata['book_id'] = book_id
    
    # Añadimos la fecha de captura actual al diccionario
    metadata['Capture Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Enviamos los metadatos a la base de datos
    db_backend.save(metadata)
    
    return metadata

if __name__ == "__main__":

    os.makedirs("data", exist_ok=True)
    
    OUTPUT_FOLDER = "data/test_datalake"
    DB_PATH = "data/metadata.db"
    
    # Inicializamos la base de datos
    current_db = SQLiteStorage(DB_PATH)
    # current_db = PostgresStorage("dbname=bigdata_project user=postgres password= ")
    # current_db = MongoStorage("mongodb://localhost:27017")
    
    # Probar con el ID 1342 (Orgullo y Prejuicio) pasando la conexión a la BD
    book_metadata = process_book(1342, OUTPUT_FOLDER, current_db)
    
    if book_metadata:
        print("Archivos de texto generados con éxito.")
        print(f"Metadatos extraídos y guardados a través de {type(current_db).__name__}:")
        print(book_metadata)