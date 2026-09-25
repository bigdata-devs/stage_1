import requests
from pathlib import Path

START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"

def download_sample_dataset(book_ids, output_path):
    successful = []
    failed = []
    for book_id in book_ids:
        try:
            header, body = fetch_book_content(book_id)
            save_book_content(book_id, header, body, output_path)
            successful.append(book_id)
            print(f"[OK] Book {book_id} downloaded successfully")
        except Exception as e:
            failed.append(book_id)
            print(f"[FAIL] Book {book_id}: {e}")
    return successful, failed

def fetch_book_content(book_id):
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    response = requests.get(url)
    response.raise_for_status()
    text = response.text
    if START_MARKER not in text or END_MARKER not in text:
        raise ValueError(f"Book {book_id} missing expected markers")
    header, body_and_footer = text.split(START_MARKER, 1)
    body, footer = body_and_footer.split(END_MARKER, 1)
    return header.strip(), body.strip()

def save_book_content(book_id, header, body, output_path):
    bodies_dir = output_path / "bodies"
    headers_dir = output_path / "headers"
    bodies_dir.mkdir(parents=True, exist_ok=True)
    headers_dir.mkdir(parents=True, exist_ok=True)
    body_path = bodies_dir / f"{book_id}_body.txt"
    header_path = headers_dir / f"{book_id}_header.txt"
    body_path.write_text(body, encoding="utf-8")
    header_path.write_text(header, encoding="utf-8")
