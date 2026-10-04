import inspect
import json
from datetime import datetime

import pytest

from src.datalake import book_fetcher, datalake_engine
from src.datalake.book_fetcher import GutenbergBook
from src.datalake.datalake_engine import (
    StoredBookFiles,
    batch_based_directory,
    book_based_directory,
    find_batch_based_book,
    find_book_based_book,
    find_time_based_book,
    list_batch_based_books,
    list_book_based_books,
    list_time_based_books,
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


def write_time_based_book(datalake_dir, hour_folder, book_id, with_header=True):
    folder = datalake_dir / hour_folder
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{book_id}_body.txt").write_text("body", encoding="utf-8")
    if with_header:
        (folder / f"{book_id}_header.txt").write_text("header", encoding="utf-8")
    return folder


class TestFindTimeBasedBook:
    def test_returns_most_recent_complete_download(self, tmp_path):
        write_time_based_book(tmp_path, "20250925/09", 7)
        newest = write_time_based_book(tmp_path, "20250926/14", 7)
        assert find_time_based_book(7, tmp_path) == StoredBookFiles(7, newest / "7_header.txt", newest / "7_body.txt")

    def test_skips_copies_without_header(self, tmp_path):
        complete = write_time_based_book(tmp_path, "20250925/09", 7)
        write_time_based_book(tmp_path, "20250926/14", 7, with_header=False)
        assert find_time_based_book(7, tmp_path).body_path == complete / "7_body.txt"

    def test_raises_when_book_is_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_time_based_book(7, tmp_path)


class TestListTimeBasedBooks:
    def test_lists_newest_complete_copy_of_each_book(self, tmp_path):
        write_time_based_book(tmp_path, "20250925/09", 7)
        newest = write_time_based_book(tmp_path, "20250926/14", 7)
        write_time_based_book(tmp_path, "20250926/14", 8)
        write_time_based_book(tmp_path, "20250926/14", 9, with_header=False)
        books = list_time_based_books(tmp_path)
        assert sorted(books) == [7, 8]
        assert books[7].body_path == newest / "7_body.txt"

    def test_ignores_other_layouts(self, tmp_path):
        store_book_based(BOOK, tmp_path)
        store_batch_based(BOOK, tmp_path)
        assert list_time_based_books(tmp_path) == {}


def book(book_id):
    return GutenbergBook(book_id, "Title: T", "Body text", f"https://example.org/{book_id}", DOWNLOADED_AT)


@pytest.fixture
def mixed_datalake(tmp_path):
    """One datalake root holding books in all three layouts, as happens when benchmarks share DATALAKE_DIR."""
    store_time_based(book(11), tmp_path)
    store_book_based(book(84), tmp_path)
    store_book_based(book(174), tmp_path)
    store_batch_based(book(1342), tmp_path)
    store_batch_based(book(2701), tmp_path)
    return tmp_path


class TestBookBasedLookup:
    def test_find_returns_files_in_book_folder(self, mixed_datalake):
        folder = mixed_datalake / "84"
        assert find_book_based_book(84, mixed_datalake) == StoredBookFiles(84, folder / "84_header.txt", folder / "84_body.txt")

    def test_find_missing_book_raises(self, mixed_datalake):
        with pytest.raises(FileNotFoundError):
            find_book_based_book(1342, mixed_datalake)

    def test_find_requires_both_files(self, mixed_datalake):
        (mixed_datalake / "84" / "84_header.txt").unlink()
        with pytest.raises(FileNotFoundError):
            find_book_based_book(84, mixed_datalake)

    def test_list_returns_only_book_based_books(self, mixed_datalake):
        assert sorted(list_book_based_books(mixed_datalake)) == [84, 174]


class TestBatchBasedLookup:
    def test_find_returns_files_in_range_folder(self, mixed_datalake):
        folder = mixed_datalake / "batch_1000_1999"
        assert find_batch_based_book(1342, mixed_datalake) == StoredBookFiles(1342, folder / "1342_header.txt", folder / "1342_body.txt")

    def test_find_uses_the_given_batch_size(self, tmp_path):
        store_batch_based(book(1342), tmp_path, batch_size=500)
        assert find_batch_based_book(1342, tmp_path, batch_size=500).body_path.parent.name == "batch_1000_1499"
        with pytest.raises(FileNotFoundError):
            find_batch_based_book(1342, tmp_path)

    def test_list_returns_only_batch_based_books(self, mixed_datalake):
        assert sorted(list_batch_based_books(mixed_datalake)) == [1342, 2701]


class TestLayoutListingsInSharedRoot:
    def test_time_based_listing_ignores_other_layouts(self, mixed_datalake):
        assert sorted(list_time_based_books(mixed_datalake)) == [11]

    def test_listings_ignore_temporary_files_of_interrupted_writes(self, mixed_datalake):
        (mixed_datalake / "84" / ".84_body.txt.x1y2.tmp").write_text("partial", encoding="utf-8")
        (mixed_datalake / "batch_0_999").mkdir()
        (mixed_datalake / "batch_0_999" / ".999_body.txt.x1y2.tmp").write_text("partial", encoding="utf-8")
        assert sorted(list_book_based_books(mixed_datalake)) == [84, 174]
        assert sorted(list_batch_based_books(mixed_datalake)) == [1342, 2701]

    def test_stored_files_leave_no_temporary_files(self, mixed_datalake):
        assert list(mixed_datalake.rglob("*.tmp")) == []
