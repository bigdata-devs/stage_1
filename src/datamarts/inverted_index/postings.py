from collections import defaultdict


def build_postings(books: dict[int, list[str]]) -> dict[str, list[int]]:
    postings: dict[str, set[int]] = defaultdict(set)
    for book_id, tokens in books.items():
        for token in tokens:
            postings[token].add(book_id)
    return {term: sorted(book_ids) for term, book_ids in postings.items()}


def merge_postings(
    index: dict[str, list[int]], new_postings: dict[str, list[int]]
) -> dict[str, list[int]]:
    """Returns a new index holding the union of both posting lists, sorted and without duplicates."""
    merged = dict(index)
    for term, book_ids in new_postings.items():
        merged[term] = sorted(set(merged.get(term, [])) | set(book_ids))
    return merged
