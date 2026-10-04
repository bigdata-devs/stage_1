import pytest

from src.utils import atomic_file
from src.utils.atomic_file import write_text_atomically


def leftover_files(folder):
    return sorted(path.name for path in folder.iterdir())


class TestWriteTextAtomically:
    def test_creates_parent_folders_and_keeps_bytes(self, tmp_path):
        target = tmp_path / "nested" / "book.txt"
        write_text_atomically(target, "line one\r\nline two\n")
        assert target.read_bytes() == b"line one\r\nline two\n"

    def test_replaces_existing_file(self, tmp_path):
        target = tmp_path / "book.txt"
        target.write_text("old", encoding="utf-8")
        write_text_atomically(target, "new")
        assert target.read_text(encoding="utf-8") == "new"
        assert leftover_files(tmp_path) == ["book.txt"]

    def test_crash_while_writing_keeps_previous_file(self, tmp_path, monkeypatch):
        target = tmp_path / "book.txt"
        target.write_text("complete old content", encoding="utf-8")

        def crash_mid_write(temporary_file, content):
            temporary_file.write(content[:3])
            raise KeyboardInterrupt

        monkeypatch.setattr(atomic_file, "_write_and_sync", crash_mid_write)
        with pytest.raises(KeyboardInterrupt):
            write_text_atomically(target, "new content that never lands")
        assert target.read_text(encoding="utf-8") == "complete old content"
        assert leftover_files(tmp_path) == ["book.txt"]

    def test_failed_swap_removes_temporary_file(self, tmp_path, monkeypatch):
        target = tmp_path / "book.txt"

        def refuse_replace(source, destination):
            raise OSError("disk full")

        monkeypatch.setattr(atomic_file.os, "replace", refuse_replace)
        with pytest.raises(OSError):
            write_text_atomically(target, "content")
        assert leftover_files(tmp_path) == []


class TestTemporaryFileHandle:
    """Windows can neither rename nor delete an open file, so these checks hold the handle order on every OS."""

    def test_is_closed_before_the_swap(self, tmp_path, monkeypatch):
        handles = []
        closed_at_swap = []
        real_write = atomic_file._write_and_sync
        real_replace = atomic_file.os.replace

        def recording_write(temporary_file, content):
            handles.append(temporary_file)
            real_write(temporary_file, content)

        def recording_replace(source, destination):
            closed_at_swap.append(handles[0].closed)
            real_replace(source, destination)

        monkeypatch.setattr(atomic_file, "_write_and_sync", recording_write)
        monkeypatch.setattr(atomic_file.os, "replace", recording_replace)
        write_text_atomically(tmp_path / "book.txt", "content")
        assert closed_at_swap == [True]

    def test_is_closed_before_an_interrupted_write_is_cleaned_up(self, tmp_path, monkeypatch):
        handles = []
        closed_at_cleanup = []
        real_remove = atomic_file._remove_leftover

        def crash_before_writing(temporary_file, content):
            handles.append(temporary_file)
            raise KeyboardInterrupt

        def recording_remove(temporary_path):
            closed_at_cleanup.append(handles[0].closed)
            real_remove(temporary_path)

        monkeypatch.setattr(atomic_file, "_write_and_sync", crash_before_writing)
        monkeypatch.setattr(atomic_file, "_remove_leftover", recording_remove)
        with pytest.raises(KeyboardInterrupt):
            write_text_atomically(tmp_path / "book.txt", "content")
        assert closed_at_cleanup == [True]
        assert leftover_files(tmp_path) == []
