// Package datamarts ports src/datamarts/inverted_index: it builds the
// inverted index once in memory and persists it in the three structures
// required by Section 4.2 (monolithic JSON file, MongoDB and a hierarchical
// folder of per-term text files).
package datamarts

import (
	"slices"
	"strconv"
	"strings"

	"search_engine_bench/utils"
)

// TokenizedBook is a book body already run through utils.ProcessText.
type TokenizedBook struct {
	ID     int
	Tokens []string
}

// LoadTokenizedBooks mirrors the loop in build_inverted_index.py: discover
// every "<id>_body.txt" in ascending ID order, read it and tokenize it. All
// token lists are kept in memory before indexing, exactly like the Python
// `books: dict[int, list[str]]`, so RAM figures stay comparable.
func LoadTokenizedBooks(bodiesDir string) ([]TokenizedBook, error) {
	bookIDs, err := utils.DiscoverBookIDs(bodiesDir)
	if err != nil {
		return nil, err
	}
	books := make([]TokenizedBook, 0, len(bookIDs))
	for _, bookID := range bookIDs {
		text, err := utils.ReadBookBody(bookID, bodiesDir)
		if err != nil {
			return nil, err
		}
		books = append(books, TokenizedBook{ID: bookID, Tokens: utils.ProcessText(text)})
	}
	return books, nil
}

// IndexEntry is one term together with its ascending, duplicate-free
// postings list of book IDs.
type IndexEntry struct {
	Term     string
	Postings []int
}

// InvertedIndex keeps its terms in first-appearance order. That is the
// iteration order of the Python dict returned by build_postings(), so the
// JSON file is written in exactly the same order as the baseline.
type InvertedIndex struct {
	entries  []IndexEntry
	position map[string]int
}

// BuildPostings mirrors build_postings() in postings.py: every term maps to
// the sorted set of books that contain it.
func BuildPostings(books []TokenizedBook) InvertedIndex {
	index := InvertedIndex{position: make(map[string]int)}
	for _, book := range books {
		index.addBook(book)
	}
	index.sortPostings()
	return index
}

func (index *InvertedIndex) addBook(book TokenizedBook) {
	for _, token := range book.Tokens {
		entry := index.entryFor(token)
		lastPosition := len(entry.Postings) - 1
		if lastPosition < 0 || entry.Postings[lastPosition] != book.ID {
			entry.Postings = append(entry.Postings, book.ID)
		}
	}
}

func (index *InvertedIndex) entryFor(term string) *IndexEntry {
	if position, found := index.position[term]; found {
		return &index.entries[position]
	}
	index.position[term] = len(index.entries)
	index.entries = append(index.entries, IndexEntry{Term: term})
	return &index.entries[len(index.entries)-1]
}

// sortPostings reproduces `sorted(set(book_ids))`, so the result is correct
// even if the caller supplies books out of order or repeats a book.
func (index *InvertedIndex) sortPostings() {
	for position := range index.entries {
		slices.Sort(index.entries[position].Postings)
		index.entries[position].Postings = slices.Compact(index.entries[position].Postings)
	}
}

// Entries returns the index entries in first-appearance order. Callers must
// treat the returned slice as read-only.
func (index InvertedIndex) Entries() []IndexEntry {
	return index.entries
}

// TermCount returns the number of unique terms.
func (index InvertedIndex) TermCount() int {
	return len(index.entries)
}

// Postings returns the postings list of a term, or an empty list.
func (index InvertedIndex) Postings(term string) []int {
	if position, found := index.position[term]; found {
		return index.entries[position].Postings
	}
	return []int{}
}

// FormatPostings renders a postings list as "[11, 84, 1342]", the format
// printed by the Rust, Java and C query commands.
func FormatPostings(postings []int) string {
	formatted := make([]string, len(postings))
	for position, bookID := range postings {
		formatted[position] = strconv.Itoa(bookID)
	}
	return "[" + strings.Join(formatted, ", ") + "]"
}
