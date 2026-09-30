"""Offline stand-ins for Project Gutenberg used by the datalake tests."""

from src.datalake.book_fetcher import END_MARKER, START_MARKER

HEADER = "Title: Sample Book\r\nAuthor: Jane Doe"
BODY = "It was a bright cold day in April.\r\nThe clocks were striking thirteen."
GUTENBERG_TEXT = f"{HEADER}\r\n{START_MARKER} SAMPLE ***\r\n{BODY}\r\n{END_MARKER} SAMPLE ***\r\nLicense footer"


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


class FakeGutenberg:
    """Replacement for ``requests.get`` that serves one canned response and records every call."""

    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[dict] = []

    def __call__(self, url: str, **kwargs) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response
