import inspect
import json
from datetime import datetime

import pytest

from src.datalake import book_fetcher, datalake_engine
from src.datalake.book_fetcher import GutenbergBook
from src.datalake.datalake_engine import (
    batch_based_directory,
    book_based_directory,
    store_batch_based,
    store_book_based,
    store_time_based,
    time_based_directory,
)
from src.datalake.errors import BookUnavailableError
from src.utils.paths import DATALAKE_DIR
from tests.test_datalake.fakes import GUTENBERG_TEXT, FakeGutenberg, FakeResponse

DOWNLOADED_AT = datetime(2025, 9, 25, 14, 30, 5)
BOOK = GutenbergBook(1342, "Title: Pride", "It is a truth\r\nuniversally acknowledged", "https://example.org/1342", DOWNLOADED_AT)


@pytest.fixture
def fake_gutenberg(monkeypatch):
    monkeypatch.setattr(book_fetcher.requests, "get", FakeGutenberg(FakeResponse(GUTENBERG_TEXT)))


class TestLayoutDirectories:
    def test_time_based_uses_date_and_hour(self, tmp_path):
        assert time_based_directory(tmp_path, DOWNLOADED_AT) == tmp_path / "20250925" / "14"

    def test_book_based_uses_book_id(self, tmp_path):
        assert book_based_directory(tmp_path, 84) == tmp_path / "84"

    @pytest.mark.parametrize("book_id, folder", [(0, "batch_0_999"), (999, "batch_0_999"), (1342, "batch_1000_1999")])
    def test_batch_based_groups_ids_by_range(self, tmp_path, book_id, folder):
        assert batch_based_directory(tmp_path, book_id) == tmp_path / folder

    def test_batch_size_must_be_positive(self, tmp_path):
        with pytest.raises(ValueError):
            batch_based_directory(tmp_path, 1, batch_size=0)

    @pytest.mark.parametrize("function_name", [
        "download_time_based", "download_book_based", "download_batch_based",
        "store_time_based", "store_book_based", "store_batch_based",
    ])
    def test_default_root_is_project_datalake(self, function_name):
        parameters = inspect.signature(getattr(datalake_engine, function_name)).parameters
        assert parameters["datalake_dir"].default == DATALAKE_DIR


class TestStoreLayouts:
    def test_time_based_writes_header_and_body(self, tmp_path):
        store_time_based(BOOK, tmp_path)
        folder = tmp_path / "20250925" / "14"
        assert (folder / "1342_header.txt").read_text(encoding="utf-8") == "Title: Pride"
        assert (folder / "1342_body.txt").read_bytes() == b"It is a truth\r\nuniversally acknowledged"

    def test_book_based_writes_metadata_file(self, tmp_path):
        store_book_based(BOOK, tmp_path)
        folder = tmp_path / "1342"
        assert (folder / "1342_body.txt").exists()
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        assert metadata == {
            "book_id": 1342,
            "source_url": "https://example.org/1342",
            "downloaded_at": "2025-09-25T14:30:05",
            "header_file": "1342_header.txt",
            "body_file": "1342_body.txt",
        }

    def test_batch_based_writes_into_range_folder(self, tmp_path):
        store_batch_based(BOOK, tmp_path, batch_size=500)
        assert sorted(path.name for path in (tmp_path / "batch_1000_1499").iterdir()) == ["1342_body.txt", "1342_header.txt"]


class TestDownloadLayouts:
    def test_time_based_download(self, fake_gutenberg, tmp_path):
        datalake_engine.download_time_based(1342, tmp_path)
        assert len(list(tmp_path.glob("*/*/1342_body.txt"))) == 1

    def test_book_based_download(self, fake_gutenberg, tmp_path):
        datalake_engine.download_book_based(84, tmp_path)
        assert sorted(path.name for path in (tmp_path / "84").iterdir()) == ["84_body.txt", "84_header.txt", "metadata.json"]

    def test_batch_based_download(self, fake_gutenberg, tmp_path):
        datalake_engine.download_batch_based(1500, tmp_path)
        assert (tmp_path / "batch_1000_1999" / "1500_body.txt").exists()

    def test_failed_download_creates_no_folders(self, monkeypatch, tmp_path):
        monkeypatch.setattr(book_fetcher.requests, "get", FakeGutenberg(FakeResponse("", 404)))
        with pytest.raises(BookUnavailableError):
            datalake_engine.download_time_based(1, tmp_path)
        assert list(tmp_path.iterdir()) == []
