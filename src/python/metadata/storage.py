import sqlite3
from pymongo import MongoClient
from abc import ABC, abstractmethod
try:
    import psycopg2
except ImportError:
    psycopg2 = None

class MetadataStorage(ABC):
    @abstractmethod
    def save(self, metadata: dict):
        pass
class SQLiteStorage(MetadataStorage):
    def __init__(self, db_path="data/metadata.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    language TEXT,
                    capture_date TEXT
                )
            ''')
            conn.commit()

    def save(self, metadata: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO books (book_id, title, author, language, capture_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metadata.get('book_id'),
                metadata.get('Title', 'Desconocido'),
                metadata.get('Author', 'Desconocido'),
                metadata.get('Language', 'Desconocido'),
                metadata.get('Capture Date', 'Desconocido')
            ))
            conn.commit()
class PostgresStorage(MetadataStorage):
    def __init__(self, connection_string):
        if psycopg2 is None:
            raise ImportError("psycopg2 is not installed; run: pip install psycopg2-binary")
        self.connection_string = connection_string
        self._initialize_db()

    def _initialize_db(self):
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        book_id INTEGER PRIMARY KEY,
                        title VARCHAR(255),
                        author VARCHAR(255),
                        language VARCHAR(50),
                        capture_date VARCHAR(50)
                    )
                ''')
            conn.commit()

    def _connect(self):
        try:
            return psycopg2.connect(self.connection_string)
        except psycopg2.Error as error:
            raise ConnectionError("Cannot connect to the Postgres server") from error

    def save(self, metadata: dict):
        with psycopg2.connect(self.connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO books (book_id, title, author, language, capture_date)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (book_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        author = EXCLUDED.author,
                        language = EXCLUDED.language,
                        capture_date = EXCLUDED.capture_date
                ''', (
                    metadata.get('book_id'),
                    metadata.get('Title', 'Desconocido'),
                    metadata.get('Author', 'Desconocido'),
                    metadata.get('Language', 'Desconocido'),
                    metadata.get('Capture Date', 'Desconocido')
                ))
            conn.commit()
class MongoStorage(MetadataStorage):
    def __init__(self, connection_string, db_name="bigdata_project"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.collection = self.db['books']

    def save(self, metadata: dict):
        self.collection.update_one(
            {"book_id": metadata.get('book_id')},
            {"$set": metadata},
            upsert=True
        )