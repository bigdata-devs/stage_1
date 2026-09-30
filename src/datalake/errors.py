"""Exceptions raised while downloading books into the datalake."""


class BookUnavailableError(Exception):
    """Raised when a book can never be downloaded, so retrying it is pointless.

    Typical causes are an ID that does not exist on Project Gutenberg (HTTP
    404) or a text without the START/END markers. The control layer records
    these IDs in its failed control file so no later run requests them again.
    """


class TransientDownloadError(Exception):
    """Raised when a download failed for a reason that may go away, so the book should be retried later.

    Typical causes are timeouts, connection errors, rate limiting (HTTP 429)
    and server errors (HTTP 5xx).
    """
