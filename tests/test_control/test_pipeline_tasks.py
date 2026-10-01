import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

from src.control import pipeline_tasks
from src.datalake.errors import BookUnavailableError, TransientDownloadError
from src.control.pipeline_tasks import BookIndexingTask, DatalakeDownloadTask
from src.datamarts.metadata.storage import SQLiteStorage
from tests.test_control.helpers import TemporaryDirectoryTestCase

HEADER = "Title: The Island Voyage\nAuthor: Jane Doe\nLanguage: English"
BODY = "The shipwreck left the crew on a lonely island."


def store_book(datalake_dir: Path, hour_folder: str, book_id: int, body: str = BODY) -> None:
    """Writes a book into a time-based datalake folder such as ``20250925/14``."""
    folder = datalake_dir / hour_folder
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{book_id}_header.txt").write_text(HEADER, encoding="utf-8")
    (folder / f"{book_id}_body.txt").write_text(body, encoding="utf-8")


class DatalakeDownloadTaskTest(TemporaryDirectoryTestCase):

    def test_downloads_into_the_given_datalake(self) -> None:
        with mock.patch.object(pipeline_tasks, "download_time_based", return_value=True) as download:
            self.assertTrue(DatalakeDownloadTask(self.work_dir).run("42"))
        download.assert_called_once_with(42, self.work_dir)

    def test_download_errors_reach_the_controller(self) -> None:
        for download_error in [BookUnavailableError("missing"), TransientDownloadError("timeout")]:
            with self.subTest(error=type(download_error).__name__):
                with mock.patch.object(pipeline_tasks, "download_time_based", side_effect=download_error):
                    with self.assertRaises(type(download_error)):
                        DatalakeDownloadTask(self.work_dir).run("42")


class BookIndexingTaskTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.datalake_dir = self.work_dir / "datalake"
        self.database_path = self.work_dir / "metadata.db"
        self.index_path = self.work_dir / "inverted_index.json"
        storage = SQLiteStorage(str(self.database_path))
        self.indexer = BookIndexingTask(self.datalake_dir, storage, self.index_path)

    def read_index(self) -> dict:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def read_metadata_rows(self) -> list:
        """Closes the connection explicitly: sqlite3's own ``with`` only commits, and an open file blocks cleanup on Windows."""
        with closing(sqlite3.connect(self.database_path)) as connection:
            return connection.execute("SELECT book_id, title, author, language, body_path FROM books").fetchall()

    def test_stores_metadata_and_terms(self) -> None:
        store_book(self.datalake_dir, "20250925/14", 5)
        self.assertTrue(self.indexer.run("5"))
        body_path = str((self.datalake_dir / "20250925" / "14" / "5_body.txt").resolve())
        self.assertEqual(self.read_metadata_rows(), [(5, "The Island Voyage", "Jane Doe", "en", body_path)])
        self.assertEqual(self.read_index()["shipwreck"], [5])
        self.assertNotIn("the", self.read_index())

    def test_merges_new_books_into_existing_index(self) -> None:
        store_book(self.datalake_dir, "20250925/14", 5)
        store_book(self.datalake_dir, "20250925/15", 12, body="Another island, no shipwreck.")
        self.indexer.run("12")
        self.indexer.run("5")
        self.assertEqual(self.read_index()["island"], [5, 12])
        self.assertEqual(self.read_index()["lonely"], [5])

    def test_reindexing_a_book_changes_nothing(self) -> None:
        store_book(self.datalake_dir, "20250925/14", 5)
        self.indexer.run("5")
        first_index = self.read_index()
        self.indexer.run("5")
        self.assertEqual(self.read_index(), first_index)
        self.assertEqual(len(self.read_metadata_rows()), 1)

    def test_missing_book_raises_without_touching_datamarts(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.indexer.run("5")
        self.assertFalse(self.index_path.exists())
        self.assertEqual(self.read_metadata_rows(), [])


if __name__ == "__main__":
    unittest.main()
