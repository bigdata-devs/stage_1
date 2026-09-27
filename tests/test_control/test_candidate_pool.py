import random
import unittest

from src.control.candidate_pool import DownloadCandidatePool, NoDownloadCandidatesError


class DownloadCandidatePoolTest(unittest.TestCase):

    def test_excludes_already_downloaded_ids(self) -> None:
        pool = DownloadCandidatePool(5, {"2", "4"}, random.Random(0))
        self.assertEqual(len(pool), 3)

    def test_draws_every_remaining_id_exactly_once(self) -> None:
        pool = DownloadCandidatePool(100, {"50"}, random.Random(0))
        drawn_ids = [pool.draw() for _ in range(99)]
        self.assertEqual(sorted(drawn_ids, key=int), [str(number) for number in range(1, 101) if number != 50])

    def test_raises_when_exhausted(self) -> None:
        pool = DownloadCandidatePool(1, set(), random.Random(0))
        pool.draw()
        self.assertTrue(pool.is_empty())
        with self.assertRaises(NoDownloadCandidatesError):
            pool.draw()

    def test_same_seed_gives_same_sequence(self) -> None:
        first_pool = DownloadCandidatePool(1000, set(), random.Random(42))
        second_pool = DownloadCandidatePool(1000, set(), random.Random(42))
        self.assertEqual([first_pool.draw() for _ in range(10)], [second_pool.draw() for _ in range(10)])


if __name__ == "__main__":
    unittest.main()
