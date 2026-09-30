import unittest
from unittest import mock

from src.control.control_file import ControlFile
from src.control.pipeline_controller import BookUnavailableError, PipelineController
from src.control.state_manager import StateManager
from src.datalake.errors import TransientDownloadError
from tests.test_control.helpers import TemporaryDirectoryTestCase, render_ids


def fail_on_odd_ids(book_id: str) -> bool:
    """Downloader stub that raises for odd book IDs."""
    if int(book_id) % 2:
        raise RuntimeError(f"Simulated download failure for {book_id}")
    return True


def reject_multiples_of_three(book_id: str) -> bool:
    """Downloader stub for which every multiple of three does not exist on Project Gutenberg."""
    if int(book_id) % 3 == 0:
        raise BookUnavailableError(f"Book {book_id} does not exist")
    return True


def reject_book_four(book_id: str) -> bool:
    """Indexer stub that reports failure for book 4 only."""
    return book_id != "4"


class PipelineControllerDecisionTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.state_manager = StateManager(self.work_dir)

    def test_indexing_takes_priority_over_downloading(self) -> None:
        self.state_manager.mark_as_downloaded("7")
        downloader = mock.Mock(return_value=True)
        PipelineController(self.state_manager, downloader_fn=downloader).run_step()
        downloader.assert_not_called()
        self.assertTrue(self.state_manager.is_indexed("7"))

    def test_processes_whole_catalogue_without_duplicates(self) -> None:
        controller = PipelineController(self.state_manager, max_book_id=50)
        controller.run_loop(steps=100)
        self.assertEqual(len(self.state_manager.get_downloaded_books()), 50)
        self.assertEqual(self.state_manager.get_indexed_books(), self.state_manager.get_downloaded_books())
        downloaded_lines = (self.work_dir / "downloaded_books.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(downloaded_lines), len(set(downloaded_lines)))

    def test_step_fails_gracefully_when_catalogue_is_exhausted(self) -> None:
        controller = PipelineController(self.state_manager, max_book_id=1)
        controller.run_loop(steps=2)
        with self.assertLogs("src.control.pipeline_controller", level="WARNING"):
            self.assertFalse(controller.run_step())

    def test_resumed_run_never_downloads_a_book_twice(self) -> None:
        PipelineController(self.state_manager, max_book_id=20).run_loop(steps=15)
        downloader = mock.Mock(return_value=True)
        PipelineController(StateManager(self.work_dir), downloader_fn=downloader, max_book_id=20).run_loop(steps=40)
        downloaded_now = {call.args[0] for call in downloader.call_args_list}
        self.assertFalse(downloaded_now & self.state_manager.get_downloaded_books())


class PipelineControllerFaultToleranceTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.state_manager = StateManager(self.work_dir)
        self.controller = PipelineController(
            self.state_manager, downloader_fn=fail_on_odd_ids, indexer_fn=reject_book_four, max_book_id=10
        )

    def test_failed_callbacks_do_not_update_state(self) -> None:
        with self.assertLogs("src.control.pipeline_controller", level="ERROR"):
            self.controller.run_loop(steps=40)
        self.assertEqual(self.state_manager.get_downloaded_books(), {"2", "4", "6", "8", "10"})
        self.assertEqual(self.state_manager.get_pending_indexing_books(), {"4"})
        self.assertNotIn("4", (self.work_dir / "indexed_books.txt").read_text(encoding="utf-8").split())

    def test_callback_exception_is_logged_with_traceback(self) -> None:
        with mock.patch.object(self.controller._random, "randrange", return_value=0):
            with self.assertLogs("src.control.pipeline_controller", level="ERROR") as captured_logs:
                self.assertFalse(self.controller.run_step())
        self.assertIn("RuntimeError", captured_logs.output[0])

    def test_keyboard_interrupt_is_not_swallowed(self) -> None:
        controller = PipelineController(self.state_manager, downloader_fn=mock.Mock(side_effect=KeyboardInterrupt))
        with self.assertRaises(KeyboardInterrupt):
            controller.run_step()
        self.assertEqual(self.state_manager.get_downloaded_books(), set())


class PipelineControllerUnavailableBookTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.state_manager = StateManager(self.work_dir)

    def run_catalogue(self, steps: int) -> None:
        controller = PipelineController(self.state_manager, downloader_fn=reject_multiples_of_three, max_book_id=9)
        with self.assertLogs("src.control.pipeline_controller", level="WARNING"):
            controller.run_loop(steps=steps)

    def test_unavailable_books_are_recorded_as_failed(self) -> None:
        self.run_catalogue(steps=30)
        self.assertEqual(self.state_manager.get_failed_books(), {"3", "6", "9"})
        self.assertEqual(self.state_manager.get_downloaded_books(), {"1", "2", "4", "5", "7", "8"})
        failed_lines = (self.work_dir / "failed_books.txt").read_text(encoding="utf-8").split()
        self.assertEqual(sorted(failed_lines, key=int), ["3", "6", "9"])

    def test_resumed_run_never_requests_a_failed_book_again(self) -> None:
        self.run_catalogue(steps=30)
        downloader = mock.Mock(return_value=True)
        resumed = PipelineController(StateManager(self.work_dir), downloader_fn=downloader, max_book_id=12)
        resumed.run_loop(steps=10)
        requested_ids = {call.args[0] for call in downloader.call_args_list}
        self.assertEqual(requested_ids, {"10", "11", "12"})

    def test_transient_errors_are_not_recorded_as_failed(self) -> None:
        controller = PipelineController(self.state_manager, downloader_fn=fail_on_odd_ids, max_book_id=4)
        with self.assertLogs("src.control.pipeline_controller", level="ERROR"):
            controller.run_loop(steps=8)
        self.assertEqual(self.state_manager.get_failed_books(), set())

    def test_transient_download_error_is_logged_and_not_recorded(self) -> None:
        downloader = mock.Mock(side_effect=TransientDownloadError("HTTP 503"))
        controller = PipelineController(self.state_manager, downloader_fn=downloader, max_book_id=3)
        with self.assertLogs("src.control.pipeline_controller", level="WARNING") as captured_logs:
            controller.run_loop(steps=3)
        self.assertEqual(self.state_manager.get_failed_books(), set())
        self.assertEqual(self.state_manager.get_downloaded_books(), set())
        self.assertIn("retried on a later run", captured_logs.output[0])

    def test_unavailable_error_from_indexer_is_a_plain_failure(self) -> None:
        self.state_manager.mark_as_downloaded("5")
        indexer = mock.Mock(side_effect=BookUnavailableError("missing"))
        controller = PipelineController(self.state_manager, indexer_fn=indexer, max_book_id=5)
        with self.assertLogs("src.control.pipeline_controller", level="WARNING"):
            self.assertFalse(controller.run_step())
        self.assertEqual(self.state_manager.get_pending_indexing_books(), {"5"})
        self.assertEqual(self.state_manager.get_failed_books(), set())


class PipelineControllerValidationTest(TemporaryDirectoryTestCase):

    def test_rejects_invalid_configuration(self) -> None:
        state_manager = StateManager(self.work_dir)
        invalid_configurations = [{"max_book_id": 0}, {"max_book_id": "5"}, {"max_download_attempts": -1}]
        for configuration in invalid_configurations:
            with self.subTest(configuration=configuration), self.assertRaises(ValueError):
                PipelineController(state_manager, **configuration)

    def test_rejects_negative_step_count(self) -> None:
        with self.assertRaises(ValueError):
            PipelineController(StateManager(self.work_dir)).run_loop(steps=-1)

    def test_accepts_legacy_positional_arguments(self) -> None:
        state_manager = StateManager(str(self.work_dir))
        PipelineController(state_manager, None, None, 100, 10).run_loop(3)
        self.assertEqual(len(state_manager.get_downloaded_books()), 2)


class PipelineControllerScalabilityTest(TemporaryDirectoryTestCase):

    def test_finishes_nearly_complete_catalogue_without_disk_reads(self) -> None:
        processed_ids = render_ids(range(1, 69991))
        (self.work_dir / "downloaded_books.txt").write_bytes(processed_ids)
        (self.work_dir / "indexed_books.txt").write_bytes(processed_ids)
        state_manager = StateManager(self.work_dir)
        with mock.patch.object(ControlFile, "_read_raw_text") as read_raw_text:
            PipelineController(state_manager).run_loop(steps=20)
        read_raw_text.assert_not_called()
        self.assertEqual(len(state_manager.get_indexed_books()), 70000)


if __name__ == "__main__":
    unittest.main()
