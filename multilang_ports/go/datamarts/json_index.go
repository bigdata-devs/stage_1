package datamarts

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
)

// SaveJSON writes the monolithic index file. The output is byte-for-byte what
// `json.dump(index, f, ensure_ascii=False, indent=2)` produces on Linux/macOS:
// terms in first-appearance order, one book ID per line, no trailing newline.
// Terms only contain [a-z], so no JSON escaping is ever needed.
func SaveJSON(index InvertedIndex, outputPath string) error {
	if err := os.MkdirAll(filepath.Dir(outputPath), directoryPermissions); err != nil {
		return fmt.Errorf("create index directory: %w", err)
	}
	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("create index file: %w", err)
	}
	defer file.Close()
	writer := bufio.NewWriter(file)
	writeJSONObject(writer, index.Entries())
	if err := writer.Flush(); err != nil {
		return fmt.Errorf("write index file: %w", err)
	}
	return file.Close()
}

func writeJSONObject(writer *bufio.Writer, entries []IndexEntry) {
	if len(entries) == 0 {
		writer.WriteString("{}")
		return
	}
	writer.WriteString("{\n")
	for position, entry := range entries {
		if position > 0 {
			writer.WriteString(",\n")
		}
		writer.WriteString(`  "` + entry.Term + `": `)
		writeJSONPostings(writer, entry.Postings)
	}
	writer.WriteString("\n}")
}

func writeJSONPostings(writer *bufio.Writer, postings []int) {
	if len(postings) == 0 {
		writer.WriteString("[]")
		return
	}
	writer.WriteString("[\n")
	for position, bookID := range postings {
		if position > 0 {
			writer.WriteString(",\n")
		}
		writer.WriteString("    " + strconv.Itoa(bookID))
	}
	writer.WriteString("\n  ]")
}

// LoadJSON mirrors load_index() in json_index.py.
func LoadJSON(indexPath string) (map[string][]int, error) {
	content, err := os.ReadFile(indexPath)
	if err != nil {
		return nil, fmt.Errorf("read index file: %w", err)
	}
	index := make(map[string][]int)
	if err := json.Unmarshal(content, &index); err != nil {
		return nil, fmt.Errorf("parse index file: %w", err)
	}
	return index, nil
}
