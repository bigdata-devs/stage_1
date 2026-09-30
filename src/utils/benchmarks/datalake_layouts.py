from abc import ABC, abstractmethod
from datetime import datetime

BATCH_SIZE = 1000

class DatalakeLayout(ABC):
    name: str

    @abstractmethod
    def store_book(self, base, book_id, header, body):
        ...

    @abstractmethod
    def locate_book(self, base, book_id):
        ...

    @abstractmethod
    def list_book_ids(self, base):
        ...

    def write_pair(self, directory, book_id, header, body):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{book_id}_header.txt").write_text(header, encoding="utf-8")
        (directory / f"{book_id}_body.txt").write_text(body, encoding="utf-8")

class TimeBasedLayout(DatalakeLayout):
    name = "time_based"

    def store_book(self, base, book_id, header, body):
        now = datetime.now()
        directory = base / now.strftime("%Y%m%d") / now.strftime("%H")
        self.write_pair(directory, book_id, header, body)

    def locate_book(self, base, book_id):
        body_paths = list(base.rglob(f"{book_id}_body.txt"))
        if body_paths:
            body_path = body_paths[0]
            header_path = body_path.with_name(f"{book_id}_header.txt")
            if header_path.exists():
                return body_path, header_path
        raise FileNotFoundError(f"Book {book_id} not found in the time-based hierarchy")

    def list_book_ids(self, base):
        return discover_bodies(base)

class BookBasedLayout(DatalakeLayout):
    name = "book_based"

    def store_book(self, base, book_id, header, body):
        self.write_pair(base / str(book_id), book_id, header, body)

    def locate_book(self, base, book_id):
        body_path = base / str(book_id) / f"{book_id}_body.txt"
        header_path = base / str(book_id) / f"{book_id}_header.txt"
        if body_path.exists() and header_path.exists():
            return body_path, header_path
        raise FileNotFoundError(f"Book {book_id} not found in the book-based hierarchy")

    def list_book_ids(self, base):
        if base.exists():
            return sorted(int(entry.name) for entry in base.iterdir() if entry.is_dir() and entry.name.isdigit())
        return []

class BatchBasedLayout(DatalakeLayout):
    name = "batch_based"

    def store_book(self, base, book_id, header, body):
        self.write_pair(base / self.batch_directory_name(book_id), book_id, header, body)

    def locate_book(self, base, book_id):
        directory = base / self.batch_directory_name(book_id)
        body_path = directory / f"{book_id}_body.txt"
        header_path = directory / f"{book_id}_header.txt"
        if body_path.exists() and header_path.exists():
            return body_path, header_path
        raise FileNotFoundError(f"Book {book_id} not found in the batch-based hierarchy")

    def list_book_ids(self, base):
        return discover_bodies(base)

    def batch_directory_name(self, book_id):
        lower_bound = (book_id // BATCH_SIZE) * BATCH_SIZE
        return f"batch_{lower_bound}_{lower_bound + BATCH_SIZE - 1}"

def discover_bodies(root):
    book_ids = {int(path.stem.replace("_body", "")) for path in root.rglob("*_body.txt")}
    return sorted(book_ids)
