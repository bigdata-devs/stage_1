"""Metadata storage backends.

``SQLiteStorage`` is the project's metadata datamart: it stores every book and
answers the queries of Section 4.1 (books by author, path of a book by title
or ID). ``PostgresStorage`` and ``MongoStorage`` implement the same schema for
the optional storage comparison and are write-only for now. Every backend saves
records in batches through ``save_many``.
"""

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator

from pymongo import ASCENDING, MongoClient, UpdateOne

from src.datamarts.metadata.book_metadata import BookMetadata, BookNotFoundError, resolve_stored_path, to_stored_path
from src.utils.paths import METADATA_DB_PATH

_COLUMNS = ("book_id", "title", "author", "language", "capture_date", "header_path", "body_path")
_COLUMN_LIST = ", ".join(_COLUMNS)
_PATH_COLUMNS = ("header_path", "body_path")
_SELECT_BOOKS = f"SELECT {_COLUMN_LIST} FROM books WHERE body_path IS NOT NULL"
_SQLITE_UPSERT = f"INSERT OR REPLACE INTO books ({_COLUMN_LIST}) VALUES ({', '.join('?' for _ in _COLUMNS)})"
_POSTGRES_UPDATES = ", ".join(f"{column} = EXCLUDED.{column}" for column in _COLUMNS[1:])
_POSTGRES_UPSERT = (f"INSERT INTO books ({_COLUMN_LIST}) VALUES ({', '.join('%s' for _ in _COLUMNS)}) "
                    f"ON CONFLICT (book_id) DO UPDATE SET {_POSTGRES_UPDATES}")
BATCH_SIZE = 1000


def _connect_postgres(connection_string):
    """Imports the PostgreSQL driver lazily so SQLite users do not need psycopg2 installed."""
    import psycopg2
    return psycopg2.connect(connection_string)


def _execute_postgres_batch(cursor, statement: str, rows: list[tuple]) -> None:
    """Sends ``rows`` in pages of ``BATCH_SIZE`` statements; imported lazily like ``_connect_postgres``."""
    from psycopg2.extras import execute_batch
    execute_batch(cursor, statement, rows, page_size=BATCH_SIZE)


def _batches(metadata_rows: Iterable[BookMetadata]) -> Iterator[list[BookMetadata]]:
    """Splits the records into consecutive lists of at most ``BATCH_SIZE`` items."""
    remaining = iter(metadata_rows)
    while batch := list(islice(remaining, BATCH_SIZE)):
        yield batch


def _to_row(metadata: BookMetadata) -> tuple:
    """Returns the column values of a record, in ``_COLUMNS`` order."""
    return (metadata.book_id, metadata.title, metadata.author, metadata.language, metadata.capture_date,
            to_stored_path(metadata.header_path), to_stored_path(metadata.body_path))


def _from_row(row: tuple) -> BookMetadata:
    """Builds a record from a row selected in ``_COLUMNS`` order."""
    book_id, title, author, language, capture_date, header_path, body_path = row
    return BookMetadata(book_id, title, author, language, capture_date,
                        resolve_stored_path(header_path), resolve_stored_path(body_path))


def _upsert_by_book_id(metadata: BookMetadata) -> UpdateOne:
    """Builds the MongoDB upsert that makes ``metadata`` the only document of its book ID."""
    document = dict(zip(_COLUMNS, _to_row(metadata)))
    return UpdateOne({"book_id": metadata.book_id}, {"$set": document}, upsert=True)


def _contains_pattern(text: str) -> str:
    """Returns a LIKE pattern matching ``text`` anywhere, with its wildcards escaped."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class MetadataStorage(ABC):
    """Anything that can persist book metadata."""

    def save(self, metadata: BookMetadata) -> None:
        """Inserts the record, replacing any previous one with the same book ID."""
        self.save_many([metadata])

    @abstractmethod
    def save_many(self, metadata_rows: Iterable[BookMetadata]) -> None:
        """Inserts the records in batches, replacing any previous ones with the same book IDs."""

    @abstractmethod
    def storage_location(self) -> str:
        """Returns where the records live: a file path, a connection string or a collection URI."""

    @abstractmethod
    def storage_size_bytes(self) -> int:
        """Returns how many bytes the stored records occupy."""


class SearchableMetadataStorage(MetadataStorage):
    """A metadata store that also answers the queries the indexing and search modules need."""

    @abstractmethod
    def find_book_by_id(self, book_id: int) -> BookMetadata:
        """Returns the record of a book.

        Raises:
            BookNotFoundError: If the book is not stored.
        """

    @abstractmethod
    def find_books_by_author(self, author: str) -> list[BookMetadata]:
        """Returns the books whose author contains ``author`` (case-insensitive), ordered by ID."""

    @abstractmethod
    def find_books_by_title(self, title: str) -> list[BookMetadata]:
        """Returns the books whose title contains ``title`` (case-insensitive), ordered by ID."""

    @abstractmethod
    def list_books(self) -> list[BookMetadata]:
        """Returns every stored book, ordered by ID."""


class SQLiteStorage(SearchableMetadataStorage):
    """Metadata datamart backed by a SQLite file (``datamarts/metadata.db`` by default)."""

    def __init__(self, db_path: Path = METADATA_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def save_many(self, metadata_rows: Iterable[BookMetadata]) -> None:
        """Writes every record with one ``executemany`` inside a single transaction."""
        with self._connection() as connection:
            connection.executemany(_SQLITE_UPSERT, (_to_row(metadata) for metadata in metadata_rows))

    def find_book_by_id(self, book_id: int) -> BookMetadata:
        books = self._select("AND book_id = ?", (book_id,))
        if not books:
            raise BookNotFoundError(f"Book {book_id} is not in the metadata store {self.db_path}")
        return books[0]

    def find_books_by_author(self, author: str) -> list[BookMetadata]:
        return self._select("AND author LIKE ? ESCAPE '\\'", (_contains_pattern(author),))

    def find_books_by_title(self, title: str) -> list[BookMetadata]:
        return self._select("AND title LIKE ? ESCAPE '\\'", (_contains_pattern(title),))

    def list_books(self) -> list[BookMetadata]:
        return self._select("", ())

    def storage_location(self) -> str:
        return str(self.db_path)

    def storage_size_bytes(self) -> int:
        return self.db_path.stat().st_size

    def _select(self, condition: str, parameters: tuple) -> list[BookMetadata]:
        """Runs the shared SELECT with an extra condition; rows without file paths are skipped."""
        with self._connection() as connection:
            rows = connection.execute(f"{_SELECT_BOOKS} {condition} ORDER BY book_id", parameters).fetchall()
        return [_from_row(row) for row in rows]

    def _initialize_db(self) -> None:
        """Creates the table, and adds the path columns to databases created by older versions."""
        with self._connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    language TEXT,
                    capture_date TEXT,
                    header_path TEXT,
                    body_path TEXT
                )
            """)
            self._add_missing_path_columns(connection)
            connection.execute("CREATE INDEX IF NOT EXISTS books_author ON books (author)")

    @staticmethod
    def _add_missing_path_columns(connection: sqlite3.Connection) -> None:
        """Migrates the schema of an existing database in place."""
        existing_columns = {row[1] for row in connection.execute("PRAGMA table_info(books)")}
        for column in _PATH_COLUMNS:
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE books ADD COLUMN {column} TEXT")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Opens a connection, commits on success and always closes it (so Windows can delete the file)."""
        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()


class PostgresStorage(MetadataStorage):
    """PostgreSQL implementation of the metadata schema, used for the optional storage comparison."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._initialize_db()

    def _initialize_db(self) -> None:
        with _connect_postgres(self.connection_string) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        book_id INTEGER PRIMARY KEY,
                        title TEXT,
                        author TEXT,
                        language TEXT,
                        capture_date TEXT,
                        header_path TEXT,
                        body_path TEXT
                    )
                """)
                for column in _PATH_COLUMNS:
                    cursor.execute(f"ALTER TABLE books ADD COLUMN IF NOT EXISTS {column} TEXT")
            connection.commit()

    def save_many(self, metadata_rows: Iterable[BookMetadata]) -> None:
        """Writes every record in pages of ``BATCH_SIZE`` upserts inside a single transaction."""
        rows = [_to_row(metadata) for metadata in metadata_rows]
        with _connect_postgres(self.connection_string) as connection:
            with connection.cursor() as cursor:
                _execute_postgres_batch(cursor, _POSTGRES_UPSERT, rows)
            connection.commit()

    def storage_location(self) -> str:
        return self.connection_string

    def storage_size_bytes(self) -> int:
        with _connect_postgres(self.connection_string) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_total_relation_size('books')")
                return cursor.fetchone()[0]


class MongoStorage(MetadataStorage):
    """MongoDB implementation of the metadata schema, used for the optional storage comparison.

    The unique index on ``book_id`` lets every upsert find its document without scanning the collection.
    """

    def __init__(self, connection_string: str, db_name: str = "bigdata_project"):
        self.connection_string = connection_string
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.collection = self.db["books"]
        self.collection.create_index([("book_id", ASCENDING)], unique=True)

    def save_many(self, metadata_rows: Iterable[BookMetadata]) -> None:
        """Sends one ordered ``bulk_write`` per ``BATCH_SIZE`` records, so the last record of a book ID wins."""
        for batch in _batches(metadata_rows):
            self.collection.bulk_write([_upsert_by_book_id(metadata) for metadata in batch])

    def storage_location(self) -> str:
        base_uri = self.connection_string.split("?")[0].rstrip("/")
        return f"{base_uri}/{self.db.name}.{self.collection.name}"

    def storage_size_bytes(self) -> int:
        stats = self.collection.database.command("collStats", self.collection.name)
        return stats["storageSize"]
