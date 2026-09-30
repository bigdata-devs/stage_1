"""Offline tests for the sample dataset downloader."""

from src.datalake import book_fetcher, download_sample_data
from tests.test_datalake.fakes import GUTENBERG_TEXT, HEADER, FakeGutenberg, FakeResponse


class TestDownloadSampleDataset:
    def test_writes_bodies_and_headers(self, monkeypatch, tmp_path):
        monkeypatch.setattr(book_fetcher.requests, "get", FakeGutenberg(FakeResponse(GUTENBERG_TEXT)))
        successful, failed = download_sample_data.download_sample_dataset([7, 9], tmp_path)
        assert successful == [7, 9]
        assert failed == []
        assert (tmp_path / "bodies" / "7_body.txt").exists()
        assert (tmp_path / "headers" / "9_header.txt").read_bytes().decode("utf-8") == HEADER

    def test_reports_permanent_and_transient_failures(self, monkeypatch, tmp_path):
        responses = {"1": FakeResponse("", 404), "2": FakeResponse("", 503), "3": FakeResponse(GUTENBERG_TEXT)}
        monkeypatch.setattr(book_fetcher.requests, "get", lambda url, **kwargs: responses[url.rsplit("pg", 1)[1][0]])
        successful, failed = download_sample_data.download_sample_dataset([1, 2, 3], tmp_path)
        assert successful == [3]
        assert failed == [1, 2]
