from abc import ABC, abstractmethod
from datetime import datetime

from src.datalake.book_fetcher import GutenbergBook
from src.datalake.datalake_engine import (
    find_batch_based_book,
    find_book_based_book,
    find_time_based_book,
    list_batch_based_books,
    list_book_based_books,
    list_time_based_books,
    store_batch_based,
    store_book_based,
    store_time_based,
)
from src.utils.benchmarks.data_source import GUTENBERG_URL

class DatalakeLayout(ABC):
    name: str

    @abstractmethod
    def store_book(self, datalake_dir, book_id, header, body):
        ...

    @abstractmethod
    def locate_book(self, datalake_dir, book_id):
        ...

    @abstractmethod
    def list_book_ids(self, datalake_dir):
        ...

class TimeBasedLayout(DatalakeLayout):
    name = "time_based"

    def store_book(self, datalake_dir, book_id, header, body):
        store_time_based(fetched_book(book_id, header, body), datalake_dir)

    def locate_book(self, datalake_dir, book_id):
        return find_time_based_book(book_id, datalake_dir)

    def list_book_ids(self, datalake_dir):
        return sorted(list_time_based_books(datalake_dir))

class BookBasedLayout(DatalakeLayout):
    name = "book_based"

    def store_book(self, datalake_dir, book_id, header, body):
        store_book_based(fetched_book(book_id, header, body), datalake_dir)

    def locate_book(self, datalake_dir, book_id):
        return find_book_based_book(book_id, datalake_dir)

    def list_book_ids(self, datalake_dir):
        return sorted(list_book_based_books(datalake_dir))

class BatchBasedLayout(DatalakeLayout):
    name = "batch_based"

    def store_book(self, datalake_dir, book_id, header, body):
        store_batch_based(fetched_book(book_id, header, body), datalake_dir)

    def locate_book(self, datalake_dir, book_id):
        return find_batch_based_book(book_id, datalake_dir)

    def list_book_ids(self, datalake_dir):
        return sorted(list_batch_based_books(datalake_dir))

def fetched_book(book_id, header, body):
    return GutenbergBook(
        book_id=book_id,
        header=header,
        body=body,
        source_url=GUTENBERG_URL.format(book_id=book_id),
        downloaded_at=datetime.now(),
    )
