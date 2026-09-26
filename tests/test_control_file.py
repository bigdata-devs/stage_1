import unittest

from src.control.control_file import ControlFile
from tests.helpers import TemporaryDirectoryTestCase, render_ids


class ControlFileReadTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.path = self.work_dir / "books.txt"
        self.control_file = ControlFile(self.path)

    def test_missing_file_reads_as_empty(self) -> None:
        self.assertEqual(self.control_file.read_ids(), [])

    def test_skips_blank_padded_duplicated_and_corrupted_lines(self) -> None:
        self.path.write_bytes(b"1\r\n  2  \n\nabc\n\xff\xfe\n2\n0003\n")
        with self.assertLogs("src.control.control_file", level="WARNING"):
            self.assertEqual(self.control_file.read_ids(), ["1", "2", "3"])

    def test_discards_torn_last_record(self) -> None:
        self.path.write_bytes(b"1\n2\n12")
        with self.assertLogs("src.control.control_file", level="WARNING") as captured_logs:
            self.assertEqual(self.control_file.read_ids(), ["1", "2"])
        self.assertIn("torn", captured_logs.output[0])


class ControlFileWriteTest(TemporaryDirectoryTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.path = self.work_dir / "books.txt"
        self.control_file = ControlFile(self.path)

    def test_append_writes_one_terminated_line_per_id(self) -> None:
        self.control_file.append("5")
        self.control_file.append("6")
        self.assertEqual(self.path.read_bytes(), b"5\n6\n")

    def test_repair_rewrites_corrupted_file_in_canonical_form(self) -> None:
        self.path.write_bytes(b"1\r\n 2\n\nabc\n2\n45")
        with self.assertLogs("src.control.control_file", level="WARNING"):
            self.control_file.repair()
        self.assertEqual(self.path.read_bytes(), b"1\n2\n")
        self.assertFalse(self.path.with_name("books.txt.tmp").exists())

    def test_repair_leaves_canonical_file_untouched(self) -> None:
        self.path.write_bytes(render_ids([1, 2]))
        modification_time = self.path.stat().st_mtime_ns
        self.control_file.repair()
        self.assertEqual(self.path.stat().st_mtime_ns, modification_time)

    def test_append_after_repair_never_merges_with_previous_line(self) -> None:
        self.path.write_bytes(b"1\n2\n12")
        with self.assertLogs("src.control.control_file", level="WARNING"):
            self.control_file.repair()
        self.control_file.append("3")
        self.assertEqual(self.control_file.read_ids(), ["1", "2", "3"])


if __name__ == "__main__":
    unittest.main()
