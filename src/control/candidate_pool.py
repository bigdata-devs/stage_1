"""Random sampling of download candidates without replacement."""

import random
from array import array
from typing import AbstractSet


class NoDownloadCandidatesError(LookupError):
    """Raised when every book ID in the configured range has already been drawn."""


class DownloadCandidatePool:
    """Holds the book IDs that have never been tried and draws them at random.

    Each draw is O(1) (swap the chosen slot with the last one, then pop), so
    picking a new book costs the same whether 0% or 99.9% of the catalogue
    has already been downloaded. IDs are stored in a compact unsigned array.
    """

    def __init__(self, max_book_id: int, excluded_ids: AbstractSet[str], rng: random.Random):
        self._rng = rng
        self._remaining_ids = array("L", (
            book_number for book_number in range(1, max_book_id + 1)
            if str(book_number) not in excluded_ids
        ))

    def __len__(self) -> int:
        return len(self._remaining_ids)

    def is_empty(self) -> bool:
        """Tells whether every candidate has already been drawn."""
        return len(self._remaining_ids) == 0

    def draw(self) -> str:
        """Removes and returns a random remaining book ID.

        Raises:
            NoDownloadCandidatesError: If the pool is exhausted.
        """
        if self.is_empty():
            raise NoDownloadCandidatesError("All book IDs in the configured range have been tried.")
        chosen_index = self._rng.randrange(len(self._remaining_ids))
        last_index = len(self._remaining_ids) - 1
        self._remaining_ids[chosen_index], self._remaining_ids[last_index] = (
            self._remaining_ids[last_index], self._remaining_ids[chosen_index]
        )
        return str(self._remaining_ids.pop())
