import pytest
import requests

from src.datalake import book_fetcher
from src.datalake.book_fetcher import REQUEST_TIMEOUT_SECONDS, fetch_and_split, split_book_text
from src.datalake.errors import BookUnavailableError, TransientDownloadError
from tests.test_datalake.fakes import BODY, GUTENBERG_TEXT, HEADER, FakeGutenberg, FakeResponse


def serve(monkeypatch, response: FakeResponse) -> FakeGutenberg:
    fake_get = FakeGutenberg(response)
    monkeypatch.setattr(book_fetcher.requests, "get", fake_get)
    return fake_get


def raise_on_get(monkeypatch, error: Exception) -> None:
    def failing_get(url, **kwargs):
        raise error

    monkeypatch.setattr(book_fetcher.requests, "get", failing_get)


class TestSplitBookText:
    def test_splits_header_and_body_and_drops_footer(self):
        header, body = split_book_text(1, GUTENBERG_TEXT)
        assert header == HEADER
        assert body.startswith("SAMPLE ***")
        assert BODY in body
        assert "License footer" not in body

    def test_missing_start_marker_is_permanent(self):
        with pytest.raises(BookUnavailableError):
            split_book_text(1, "no markers at all")

    def test_end_marker_before_start_marker_is_permanent(self):
        text = f"{book_fetcher.END_MARKER} ***\nheader\n{book_fetcher.START_MARKER} ***\nbody"
        with pytest.raises(BookUnavailableError):
            split_book_text(1, text)


class TestFetchAndSplit:
    def test_returns_split_book_with_source_details(self, monkeypatch):
        serve(monkeypatch, FakeResponse(GUTENBERG_TEXT))
        book = fetch_and_split(1342)
        assert book.book_id == 1342
        assert book.header == HEADER
        assert BODY in book.body
        assert book.source_url == "https://www.gutenberg.org/cache/epub/1342/pg1342.txt"

    def test_every_request_has_a_timeout(self, monkeypatch):
        fake_get = serve(monkeypatch, FakeResponse(GUTENBERG_TEXT))
        fetch_and_split(1342)
        assert fake_get.calls[0]["timeout"] == REQUEST_TIMEOUT_SECONDS

    @pytest.mark.parametrize("status_code", [400, 403, 404, 410])
    def test_client_errors_are_permanent(self, monkeypatch, status_code):
        serve(monkeypatch, FakeResponse("", status_code))
        with pytest.raises(BookUnavailableError):
            fetch_and_split(1)

    @pytest.mark.parametrize("status_code", [408, 429, 500, 502, 503])
    def test_server_errors_and_throttling_are_transient(self, monkeypatch, status_code):
        serve(monkeypatch, FakeResponse("", status_code))
        with pytest.raises(TransientDownloadError):
            fetch_and_split(1)

    def test_text_without_markers_is_permanent(self, monkeypatch):
        serve(monkeypatch, FakeResponse("Just some text"))
        with pytest.raises(BookUnavailableError):
            fetch_and_split(1)

    @pytest.mark.parametrize("network_error", [requests.Timeout("slow"), requests.ConnectionError("down")])
    def test_network_errors_are_transient(self, monkeypatch, network_error):
        raise_on_get(monkeypatch, network_error)
        with pytest.raises(TransientDownloadError):
            fetch_and_split(1)
