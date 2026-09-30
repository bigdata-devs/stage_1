"""Crash-safe file replacement: readers see either the old file or the complete new one, never a truncated file."""

import os
import tempfile
from pathlib import Path

TEMPORARY_SUFFIX = ".tmp"
_ENCODING = "utf-8"


def write_text_atomically(file_path: Path, content: str) -> None:
    """Writes UTF-8 text through a temporary sibling file that is fsync-ed and then swapped in with ``os.replace``.

    The parent folder is created if needed and newlines are written as given
    (no translation), so the bytes are identical on every OS. The temporary
    file starts with a dot and ends in ``.tmp``, so datalake and index globs
    never mistake it for a real book or term file.
    """
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=TEMPORARY_SUFFIX)
    try:
        _write_and_sync(file_descriptor, content)
        os.replace(temporary_name, target)
    except BaseException:
        _remove_leftover(Path(temporary_name))
        raise


def _write_and_sync(file_descriptor: int, content: str) -> None:
    """Writes the content to an open descriptor and forces it to disk before the swap."""
    with open(file_descriptor, "w", encoding=_ENCODING, newline="") as temporary_file:
        temporary_file.write(content)
        temporary_file.flush()
        os.fsync(temporary_file.fileno())


def _remove_leftover(temporary_path: Path) -> None:
    """Deletes the temporary file of a failed write, if it still exists."""
    temporary_path.unlink(missing_ok=True)
