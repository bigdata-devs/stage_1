package datamarts

import (
	"bufio"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const (
	directoryPermissions = 0o755
	filePermissions      = 0o644
	termFileExtension    = ".txt"
	reservedNameEscape   = "_"
)

// windowsReservedNames mirrors WINDOWS_RESERVED_NAMES in folder_index.py:
// Windows refuses these device names as file names whatever their
// extension, so their term files get a trailing underscore
// ("con" -> "C/con_.txt"). Terms only contain letters, so the escaped name
// can never clash with a real term.
var windowsReservedNames = reservedNameSet()

func reservedNameSet() map[string]bool {
	names := map[string]bool{"con": true, "prn": true, "aux": true, "nul": true}
	for number := 1; number <= 9; number++ {
		names[fmt.Sprintf("com%d", number)] = true
		names[fmt.Sprintf("lpt%d", number)] = true
	}
	return names
}

// termFileName returns the file name of a term, escaping Windows-reserved
// names exactly like term_file_name() in folder_index.py.
func termFileName(term string) string {
	if windowsReservedNames[strings.ToLower(term)] {
		return term + reservedNameEscape + termFileExtension
	}
	return term + termFileExtension
}

// SaveFolder mirrors save_index() in folder_index.py: one "<term>.txt" file
// per term, grouped in a sub-folder named after the upper-cased first letter
// (e.g. "A/adventure.txt"). Each file holds one book ID per line and ends
// with a newline.
func SaveFolder(index InvertedIndex, outputDir string) error {
	if err := os.MkdirAll(outputDir, directoryPermissions); err != nil {
		return fmt.Errorf("create folder index: %w", err)
	}
	createdLetters := make(map[string]bool)
	for _, entry := range index.Entries() {
		letterDir := filepath.Join(outputDir, termLetter(entry.Term))
		if !createdLetters[letterDir] {
			if err := os.MkdirAll(letterDir, directoryPermissions); err != nil {
				return fmt.Errorf("create %s: %w", letterDir, err)
			}
			createdLetters[letterDir] = true
		}
		if err := writeTermFile(filepath.Join(letterDir, termFileName(entry.Term)), entry.Postings); err != nil {
			return err
		}
	}
	return nil
}

func termLetter(term string) string {
	return strings.ToUpper(term[:1])
}

func writeTermFile(path string, postings []int) error {
	var content strings.Builder
	for _, bookID := range postings {
		content.WriteString(strconv.Itoa(bookID))
		content.WriteByte('\n')
	}
	if err := os.WriteFile(path, []byte(content.String()), filePermissions); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}

// QueryFolder mirrors query_index() in folder_index.py: it opens only the
// file of the requested term and returns an empty list if it does not exist.
func QueryFolder(term string, indexDir string) ([]int, error) {
	if term == "" {
		return []int{}, nil
	}
	termFile := filepath.Join(indexDir, termLetter(term), termFileName(term))
	postings, err := readTermFile(termFile)
	if errors.Is(err, fs.ErrNotExist) {
		return []int{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", termFile, err)
	}
	return postings, nil
}

// UpdateFolder merges one book into the folder index, like add_book(): for
// every term it reads the postings file, adds the book ID in sorted order
// and rewrites the file.
func UpdateFolder(bookID int, tokens []string, indexDir string) error {
	for _, term := range UniqueTerms(tokens) {
		letterDir := filepath.Join(indexDir, termLetter(term))
		if err := os.MkdirAll(letterDir, directoryPermissions); err != nil {
			return fmt.Errorf("create %s: %w", letterDir, err)
		}
		termFile := filepath.Join(letterDir, termFileName(term))
		postings, err := readTermFile(termFile)
		if err != nil && !errors.Is(err, fs.ErrNotExist) {
			return fmt.Errorf("open %s: %w", termFile, err)
		}
		if err := writeTermFile(termFile, AppendSortedUnique(postings, bookID)); err != nil {
			return err
		}
	}
	return nil
}

func readTermFile(path string) ([]int, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	return readPostingLines(file)
}

func readPostingLines(file *os.File) ([]int, error) {
	postings := []int{}
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		bookID, err := strconv.Atoi(line)
		if err != nil {
			return nil, fmt.Errorf("invalid book id %q in %s: %w", line, file.Name(), err)
		}
		postings = append(postings, bookID)
	}
	return postings, scanner.Err()
}
