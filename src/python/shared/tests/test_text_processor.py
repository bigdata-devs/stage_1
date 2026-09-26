import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.text_processor import tokenize, normalize, process_text


class TestTokenize:
    def test_converts_to_lowercase(self):
        assert tokenize("HELLO World") == ["hello", "world"]

    def test_removes_punctuation(self):
        assert tokenize("hello, world!") == ["hello", "world"]

    def test_removes_hyphens(self):
        assert tokenize("well-known") == ["well", "known"]

    def test_handles_empty_string(self):
        assert tokenize("") == []

    def test_keeps_alphanumeric_words(self):
        assert tokenize("word123 another") == ["word", "another"]


class TestNormalize:
    def test_removes_stopwords(self):
        tokens = ["the", "cat", "is", "on", "the", "mat"]
        assert normalize(tokens) == ["cat", "mat"]

    def test_removes_roman_numerals(self):
        tokens = ["chapter", "ii", "introduction"]
        assert normalize(tokens) == ["chapter", "introduction"]

    def test_removes_single_characters(self):
        tokens = ["a", "big", "b", "cat"]
        assert normalize(tokens) == ["big", "cat"]

    def test_preserves_valid_words(self):
        tokens = ["adventure", "island", "shipwreck"]
        assert normalize(tokens) == ["adventure", "island", "shipwreck"]

    def test_filters_number_words_in_stopwords(self):
        tokens = ["one", "two", "three", "hundred", "forty"]
        result = normalize(tokens)
        assert "hundred" in result
        assert "forty" in result
        assert "one" not in result
        assert "two" not in result
        assert "three" not in result


class TestProcessText:
    def test_full_pipeline(self):
        text = "The Cat is on the Mat, Chapter II!"
        result = process_text(text)
        assert "cat" in result
        assert "mat" in result
        assert "chapter" in result
        assert "the" not in result
        assert "is" not in result
        assert "ii" not in result

    def test_handles_gutenberg_header(self):
        text = "Title: Pride and Prejudice Author: Jane Austen"
        result = process_text(text)
        assert "pride" in result
        assert "prejudice" in result
        assert "jane" in result
        assert "austen" in result
        assert "and" not in result
