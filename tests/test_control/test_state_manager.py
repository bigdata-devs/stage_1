import unittest
from unittest import mock

from src.control.book_id import InvalidBookIdError
from src.control.control_file import ControlFile
from src.control.state_manager import StateManager
from tests.test_control.helpers import TemporaryDirectoryTestCase, render_ids


class StateManagerLoadTest(TemporaryDirectoryTestCase):

    def test_creates_control_directory(self) -> None:
        control_dir = self.work_dir / "nested" / "control"
        StateManager(str(control_dir))
        self.assertTrue(control_dir.is_dir())

    def test_loads_and_repairs_corrupted_control_files(self) -> None:
        (self.work_dir / "downloaded_books.txt").write_bytes(b"1\r\n  2  \n\nabc\n2\n0003\n45")
        with self.assertLogs("src.control", level="WARNING"):
            state_manager = StateManager(self.work_dir)
        self.assertEqual(state_manager.get_downloaded_books(), {"1", "2", "3"})
        self.assertEqual((self.work_dir / "downloaded_books.txt").read_bytes(), render_ids([1, 2, 3]))

    def test_warns_about_indexed_books_that_were_never_downloaded(self) -> None:
        (self.work_dir / "indexed_books.txt").write_bytes(render_ids([9]))
        with self.assertLogs("src.control.state_manager", level="WARNING"):
            StateManager(self.work_dir)


class StateManagerUpdateTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.state_manager = StateManager(self.work_dir)

    def test_mark_as_downloaded_is_idempotent_and_normalized(self) -> None:
        for raw_book_id in ["5", 5, " 05 "]:
            self.state_manager.mark_as_downloaded(raw_book_id)
        self.assertEqual((self.work_dir / "downloaded_books.txt").read_bytes(), render_ids([5]))

    def test_pending_books_follow_state_changes(self) -> None:
        self.state_manager.mark_as_downloaded("5")
        self.state_manager.mark_as_downloaded("6")
        self.state_manager.mark_as_indexed("5")
        self.assertEqual(self.state_manager.get_pending_indexing_books(), {"6"})
        self.assertTrue(self.state_manager.is_indexed("5"))

    def test_rejects_invalid_ids_without_touching_disk(self) -> None:
        with self.assertRaises(InvalidBookIdError):
            self.state_manager.mark_as_downloaded("not-an-id")
        self.assertFalse((self.work_dir / "downloaded_books.txt").exists())

    def test_returned_sets_are_copies(self) -> None:
        self.state_manager.mark_as_downloaded("5")
        self.state_manager.get_pending_indexing_books().clear()
        self.state_manager.get_downloaded_books().clear()
        self.assertEqual(self.state_manager.get_pending_indexing_books(), {"5"})
        self.assertEqual(self.state_manager.get_downloaded_books(), {"5"})

    def test_failed_disk_write_leaves_cache_unchanged(self) -> None:
        with mock.patch.object(ControlFile, "append", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.state_manager.mark_as_downloaded("5")
        self.assertFalse(self.state_manager.is_downloaded("5"))


class StateManagerCachingTest(TemporaryDirectoryTestCase):

    def test_queries_never_read_from_disk_after_loading(self) -> None:
        state_manager = StateManager(self.work_dir)
        with mock.patch.object(ControlFile, "_read_raw_text") as read_raw_text:
            state_manager.mark_as_downloaded("5")
            state_manager.get_pending_indexing_books()
            state_manager.is_downloaded("5")
        read_raw_text.assert_not_called()

    def test_new_instance_resumes_from_persisted_state(self) -> None:
        first_run = StateManager(self.work_dir)
        first_run.mark_as_downloaded("5")
        first_run.mark_as_downloaded("6")
        first_run.mark_as_indexed("5")
        self.assertEqual(StateManager(self.work_dir).get_pending_indexing_books(), {"6"})


if __name__ == "__main__":
    unittest.main()
