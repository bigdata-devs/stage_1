package utils

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

// BodySuffix is the file-name suffix of every book body in the datalake,
// shared with the Python, Rust, Java and C implementations.
const BodySuffix = "_body.txt"

// HeaderSuffix is the file-name suffix of every book header in the datalake.
const HeaderSuffix = "_header.txt"

// BodyFileName returns "<bookID>_body.txt".
func BodyFileName(bookID int) string {
	return strconv.Itoa(bookID) + BodySuffix
}

// HeaderFileName returns "<bookID>_header.txt".
func HeaderFileName(bookID int) string {
	return strconv.Itoa(bookID) + HeaderSuffix
}

// ReadBookBody mirrors read_book_body() in src/utils/body_files.py.
func ReadBookBody(bookID int, bodiesDir string) (string, error) {
	return readBookFile(bookID, bodiesDir, BodySuffix)
}

// ReadBookHeader reads "<bookID>_header.txt" from a corpus directory.
func ReadBookHeader(bookID int, headersDir string) (string, error) {
	return readBookFile(bookID, headersDir, HeaderSuffix)
}

func readBookFile(bookID int, directory string, suffix string) (string, error) {
	content, err := os.ReadFile(filepath.Join(directory, strconv.Itoa(bookID)+suffix))
	if err != nil {
		return "", fmt.Errorf("read %s of book %d: %w", suffix, bookID, err)
	}
	return string(content), nil
}

// DiscoverBookIDs mirrors discover_book_ids() in src/utils/body_files.py:
// it returns the ascending IDs of every "<id>_body.txt" file in bodiesDir.
func DiscoverBookIDs(bodiesDir string) ([]int, error) {
	entries, err := os.ReadDir(bodiesDir)
	if err != nil {
		return nil, fmt.Errorf("list bodies directory: %w", err)
	}
	bookIDs := make([]int, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), BodySuffix) {
			continue
		}
		bookID, err := parseBookID(entry.Name())
		if err != nil {
			return nil, err
		}
		bookIDs = append(bookIDs, bookID)
	}
	sort.Ints(bookIDs)
	return bookIDs, nil
}

func parseBookID(bodyFileName string) (int, error) {
	rawID := strings.TrimSuffix(bodyFileName, BodySuffix)
	bookID, err := strconv.Atoi(rawID)
	if err != nil {
		return 0, fmt.Errorf("invalid book id in %q: %w", bodyFileName, err)
	}
	return bookID, nil
}
