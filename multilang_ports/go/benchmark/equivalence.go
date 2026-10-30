// Equivalence writes the canonical file that the cross-language checker
// compares byte for byte: the token stream of every sample book, the posting
// lists built from them and the result of every shared query. It reuses the
// exact tokenizer, postings builder and query intersection of the timed
// suite, so a file identical to the other languages' proves the harness
// measures the same work everywhere.
package benchmark

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"search_engine_bench/datamarts"
	"search_engine_bench/utils"
)

// RunEquivalence implements `search_engine_bench equivalence`, the Go side of
// the cross-language equivalence contract.
func RunEquivalence(bodiesDir, bookIDsPath, queriesPath, outputPath string) error {
	bookIDs, err := loadBookIDs(bookIDsPath)
	if err != nil {
		return err
	}
	books, err := tokenizeBooks(bodiesDir, bookIDs)
	if err != nil {
		return err
	}
	queries, err := LoadSharedQueries(queriesPath)
	if err != nil {
		return err
	}
	return writeCanonicalFile(outputPath, books, queries)
}

func loadBookIDs(bookIDsPath string) ([]int, error) {
	content, err := os.ReadFile(bookIDsPath)
	if err != nil {
		return nil, err
	}
	var bookIDs []int
	for _, line := range strings.Split(string(content), "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		bookID, err := strconv.Atoi(trimmed)
		if err != nil {
			return nil, fmt.Errorf("%s: invalid book id %q", bookIDsPath, trimmed)
		}
		bookIDs = append(bookIDs, bookID)
	}
	return bookIDs, nil
}

func tokenizeBooks(bodiesDir string, bookIDs []int) ([]datamarts.TokenizedBook, error) {
	books := make([]datamarts.TokenizedBook, 0, len(bookIDs))
	for _, bookID := range bookIDs {
		text, err := utils.ReadBookBody(bookID, bodiesDir)
		if err != nil {
			return nil, err
		}
		books = append(books, datamarts.TokenizedBook{ID: bookID, Tokens: utils.ProcessText(text)})
	}
	return books, nil
}

func writeCanonicalFile(outputPath string, books []datamarts.TokenizedBook,
	queries [][]string) error {
	file, err := os.Create(filepath.Clean(outputPath))
	if err != nil {
		return err
	}
	writer := bufio.NewWriter(file)
	index := datamarts.BuildPostings(books)
	if err := writeTokenLines(writer, books); err != nil {
		file.Close()
		return err
	}
	if err := writePostingsLines(writer, index); err != nil {
		file.Close()
		return err
	}
	if err := writeQueryLines(writer, queries, index); err != nil {
		file.Close()
		return err
	}
	if err := writer.Flush(); err != nil {
		file.Close()
		return err
	}
	return file.Close()
}

func writeTokenLines(writer *bufio.Writer, books []datamarts.TokenizedBook) error {
	for _, book := range books {
		if _, err := fmt.Fprintf(writer, "tokens\t%d\t%s\n", book.ID,
			strings.Join(book.Tokens, "\t")); err != nil {
			return err
		}
	}
	return nil
}

func writePostingsLines(writer *bufio.Writer, index datamarts.InvertedIndex) error {
	entries := slices.Clone(index.Entries())
	slices.SortFunc(entries, func(left, right datamarts.IndexEntry) int {
		return strings.Compare(left.Term, right.Term)
	})
	for _, entry := range entries {
		if _, err := fmt.Fprintf(writer, "postings\t%s\t%s\n", entry.Term,
			joinIDs(entry.Postings)); err != nil {
			return err
		}
	}
	return nil
}

func writeQueryLines(writer *bufio.Writer, queries [][]string,
	index datamarts.InvertedIndex) error {
	for ordinal, terms := range queries {
		matched, err := intersectPostings(terms, func(term string) ([]int, error) {
			return index.Postings(term), nil
		})
		if err != nil {
			return err
		}
		suffix := ""
		if len(matched) > 0 {
			suffix = "\t" + joinIDs(matched)
		}
		if _, err := fmt.Fprintf(writer, "query\t%d%s\n", ordinal+1, suffix); err != nil {
			return err
		}
	}
	return nil
}

func joinIDs(bookIDs []int) string {
	formatted := make([]string, len(bookIDs))
	for position, bookID := range bookIDs {
		formatted[position] = strconv.Itoa(bookID)
	}
	return strings.Join(formatted, ",")
}
