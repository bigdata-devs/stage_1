// Package utils holds the helpers shared by the datalake and datamart ports:
// the tokenizer/normalizer and the body-file discovery logic.
//
// Every rule here mirrors src/utils/text_processor.py so that all language
// ports feed exactly the same token stream into the inverted index.
package utils

import "strings"

// romanNumerals mirrors _ROMAN_NUMERALS in src/utils/text_processor.py.
var romanNumerals = newWordSet(
	"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
	"xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
	"xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii", "xxviii", "xxix", "xxx",
	"xl", "l", "lx", "lxx", "lxxx", "xc", "c",
)

// stopWords mirrors STOP_WORDS in src/utils/text_processor.py.
var stopWords = newWordSet(
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
	"same", "now", "new", "one", "two", "three", "many", "much",
	"well", "back", "even", "still", "before", "after", "between", "through",
)

// pythonSpecialLowercase reproduces the one unconditional multi-rune mapping
// of Python's str.lower() that Go's strings.ToLower does not apply:
// U+0130 (İ) becomes "i" followed by U+0307 (combining dot above). Without it
// Go would glue the "i" to the following letters and emit a different token.
var pythonSpecialLowercase = strings.NewReplacer("\u0130", "i\u0307")

type wordSet map[string]struct{}

func newWordSet(words ...string) wordSet {
	set := make(wordSet, len(words))
	for _, word := range words {
		set[word] = struct{}{}
	}
	return set
}

func (set wordSet) contains(word string) bool {
	_, found := set[word]
	return found
}

// Tokenize lowercases the text and returns every maximal run of ASCII letters
// [a-z]+, exactly like `re.findall(r"[a-z]+", text.lower())`.
func Tokenize(text string) []string {
	lowered := strings.ToLower(pythonSpecialLowercase.Replace(text))
	tokens := make([]string, 0, len(lowered)/6)
	runStart := -1
	for position := 0; position < len(lowered); position++ {
		if isASCIILowercase(lowered[position]) {
			if runStart < 0 {
				runStart = position
			}
			continue
		}
		if runStart >= 0 {
			tokens = append(tokens, lowered[runStart:position])
			runStart = -1
		}
	}
	if runStart >= 0 {
		tokens = append(tokens, lowered[runStart:])
	}
	return tokens
}

// isASCIILowercase works on raw bytes: every byte of a multi-byte UTF-8 rune
// is >= 0x80, so non-ASCII characters always break a run, as in the regex.
func isASCIILowercase(character byte) bool {
	return character >= 'a' && character <= 'z'
}

// Normalize drops stop words, Roman numerals and single-letter tokens.
func Normalize(tokens []string) []string {
	kept := make([]string, 0, len(tokens))
	for _, token := range tokens {
		if shouldKeep(token) {
			kept = append(kept, token)
		}
	}
	return kept
}

func shouldKeep(token string) bool {
	return len(token) > 1 && !stopWords.contains(token) && !romanNumerals.contains(token)
}

// ProcessText runs the full pipeline: Tokenize followed by Normalize.
func ProcessText(text string) []string {
	return Normalize(Tokenize(text))
}
