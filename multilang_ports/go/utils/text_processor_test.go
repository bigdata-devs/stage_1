package utils

import (
	"reflect"
	"testing"
)

// The cases mirror tests/test_utils/test_text_processor.py.

func TestTokenizeConvertsToLowercase(t *testing.T) {
	assertTokens(t, Tokenize("HELLO World"), "hello", "world")
}

func TestTokenizeRemovesPunctuation(t *testing.T) {
	assertTokens(t, Tokenize("hello, world!"), "hello", "world")
}

func TestTokenizeRemovesHyphens(t *testing.T) {
	assertTokens(t, Tokenize("well-known"), "well", "known")
}

func TestTokenizeHandlesEmptyString(t *testing.T) {
	assertTokens(t, Tokenize(""))
}

func TestTokenizeKeepsAlphabeticPartOfAlphanumericWords(t *testing.T) {
	assertTokens(t, Tokenize("word123 another"), "word", "another")
}

func TestTokenizeSplitsOnNonASCIILetters(t *testing.T) {
	assertTokens(t, Tokenize("café naïve"), "caf", "na", "ve")
}

func TestTokenizeFollowsPythonLowercaseOfDottedCapitalI(t *testing.T) {
	// Python: "İstanbul".lower() == "i̇stanbul" -> ["i", "stanbul"].
	assertTokens(t, Tokenize("\u0130stanbul"), "i", "stanbul")
}

func TestTokenizeLowercasesKelvinSignLikePython(t *testing.T) {
	// U+212A KELVIN SIGN lowercases to ASCII "k" in both languages.
	assertTokens(t, Tokenize("\u212Aey"), "key")
}

func TestNormalizeRemovesStopWords(t *testing.T) {
	assertTokens(t, Normalize([]string{"the", "cat", "is", "on", "the", "mat"}), "cat", "mat")
}

func TestNormalizeRemovesRomanNumerals(t *testing.T) {
	assertTokens(t, Normalize([]string{"chapter", "ii", "introduction"}), "chapter", "introduction")
}

func TestNormalizeRemovesSingleCharacters(t *testing.T) {
	assertTokens(t, Normalize([]string{"a", "big", "b", "cat"}), "big", "cat")
}

func TestNormalizePreservesValidWords(t *testing.T) {
	assertTokens(t, Normalize([]string{"adventure", "island", "shipwreck"}), "adventure", "island", "shipwreck")
}

func TestNormalizeFiltersNumberWordsInStopWords(t *testing.T) {
	assertTokens(t, Normalize([]string{"one", "two", "three", "hundred", "forty"}), "hundred", "forty")
}

func TestProcessTextRunsFullPipeline(t *testing.T) {
	assertTokens(t, ProcessText("The Cat is on the Mat, Chapter II!"), "cat", "mat", "chapter")
}

func assertTokens(t *testing.T, actual []string, expected ...string) {
	t.Helper()
	if expected == nil {
		expected = []string{}
	}
	if !reflect.DeepEqual(actual, expected) {
		t.Fatalf("expected %q, got %q", expected, actual)
	}
}
