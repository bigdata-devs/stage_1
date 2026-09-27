"""Offline tests for the datalake download helpers."""

import pytest

from src.datalake import datalake_engine, download_sample_data
from src.datalake.download_sample_data import START_MARKER, END_MARKER

HEADER = "Title: Sample Book\nAuthor: Jane Doe"
BODY = "It was a bright cold day in April."
GUTENBERG_TEXT = f"{HEADER}\n{START_MARKER} SAMPLE ***\n{BODY}\n{END_MARKER} SAMPLE ***\nLicense footer"


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def fake_gutenberg(monkeypatch):
    def fake_get(url, *args, **kwargs):
        return FakeResponse(GUTENBERG_TEXT)

    monkeypatch.setattr(download_sample_data.requests, "get", fake_get)
    monkeypatch.setattr(datalake_engine.requests, "get", fake_get)


class TestFetchBookContent:
    def test_splits_header_and_body(self, fake_gutenberg):
        header, body = download_sample_data.fetch_book_content(1)
        assert header == HEADER
        assert body.startswith("SAMPLE ***")
        assert BODY in body
        assert "License footer" not in body

    def test_rejects_text_without_markers(self, monkeypatch):
        monkeypatch.setattr(download_sample_data.requests, "get", lambda url: FakeResponse("no markers"))
        with pytest.raises(ValueError):
            download_sample_data.fetch_book_content(1)


class TestDownloadSampleDataset:
    def test_writes_bodies_and_headers(self, fake_gutenberg, tmp_path):
        successful, failed = download_sample_data.download_sample_dataset([7, 9], tmp_path)
        assert successful == [7, 9]
        assert failed == []
        assert (tmp_path / "bodies" / "7_body.txt").exists()
        assert (tmp_path / "headers" / "9_header.txt").read_text(encoding="utf-8") == HEADER

    def test_reports_failures(self, monkeypatch, tmp_path):
        monkeypatch.setattr(download_sample_data.requests, "get", lambda url: FakeResponse("", 404))
        successful, failed = download_sample_data.download_sample_dataset([7], tmp_path)
        assert successful == []
        assert failed == [7]


class TestDatalakeEngine:
    def test_book_based_layout(self, fake_gutenberg, tmp_path):
        assert datalake_engine.download_book_based(84, str(tmp_path)) is True
        assert (tmp_path / "84" / "84_body.txt").exists()
        assert (tmp_path / "84" / "84_header.txt").exists()

    def test_batch_based_layout(self, fake_gutenberg, tmp_path):
        assert datalake_engine.download_batch_based(1500, str(tmp_path)) is True
        assert (tmp_path / "batch_1000_1999" / "1500_body.txt").exists()

    def test_time_based_layout(self, fake_gutenberg, tmp_path):
        assert datalake_engine.download_time_based(1342, str(tmp_path)) is True
        body_files = list(tmp_path.glob("*/*/1342_body.txt"))
        assert len(body_files) == 1
