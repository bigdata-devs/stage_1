from collections import defaultdict


def build_postings(books: dict[int, list[str]]) -> dict[str, list[int]]:
    postings: dict[str, set[int]] = defaultdict(set)
    for book_id, tokens in books.items():
        for token in tokens:
            postings[token].add(book_id)
    return {term: sorted(book_ids) for term, book_ids in postings.items()}
