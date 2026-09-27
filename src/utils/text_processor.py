import re

_ROMAN_NUMERALS = frozenset({
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii", "xxviii", "xxix", "xxx",
    "xl", "l", "lx", "lxx", "lxxx", "xc", "c",
})

STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "it", "its", "he", "she",
    "they", "them", "his", "her", "their", "this", "that", "these", "those",
    "i", "you", "we", "me", "my", "your", "our", "not", "no", "so",
    "if", "then", "than", "too", "very", "just", "about", "also",
    "as", "from", "into", "up", "out", "off", "over", "under", "again",
    "there", "here", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "only", "own",
    "same", "so", "now", "new", "one", "two", "three", "many", "much",
    "well", "back", "even", "still", "before", "after", "between", "through",
})

_TOKEN_PATTERN = re.compile(r"[a-z]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def normalize(tokens: list[str]) -> list[str]:
    return [
        token for token in tokens
        if token not in STOP_WORDS
        and token not in _ROMAN_NUMERALS
        and len(token) > 1
    ]


def process_text(text: str) -> list[str]:
    tokens = tokenize(text)
    return normalize(tokens)
