import unittest

from src.control.book_id import InvalidBookIdError, is_valid_book_id, normalize_book_id


class NormalizeBookIdTest(unittest.TestCase):

    def test_strips_whitespace_and_leading_zeros(self) -> None:
        self.assertEqual(normalize_book_id(" 0042 "), "42")

    def test_accepts_integers(self) -> None:
        self.assertEqual(normalize_book_id(7), "7")

    def test_rejects_malformed_values(self) -> None:
        malformed_values = ["", "   ", "abc", "12a", "-3", "+3", "1.5", "1 2", "0", "000", "٣", True]
        for malformed_value in malformed_values:
            with self.subTest(value=malformed_value), self.assertRaises(InvalidBookIdError):
                normalize_book_id(malformed_value)

    def test_invalid_book_id_error_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(InvalidBookIdError, ValueError))


class IsValidBookIdTest(unittest.TestCase):

    def test_reports_validity_without_raising(self) -> None:
        self.assertTrue(is_valid_book_id("1342"))
        self.assertFalse(is_valid_book_id("not-an-id"))


if __name__ == "__main__":
    unittest.main()
