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

        def crash_mid_write(file_descriptor, content):
            with open(file_descriptor, "w", encoding="utf-8") as partial_file:
                partial_file.write(content[:3])
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
