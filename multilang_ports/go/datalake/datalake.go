package datalake

import (
	"fmt"
	"os"
	"path/filepath"

	"search_engine_bench/utils"
)

const (
	directoryPermissions = 0o755
	filePermissions      = 0o644
)

// Datalake is a root folder organised according to one Layout.
type Datalake struct {
	Root   string
	Layout Layout
}

// Download mirrors download_time_based/download_book_based/
// download_batch_based(): fetch the raw book, split it and store both parts.
func (lake Datalake) Download(fetcher Fetcher, bookID int) (string, error) {
	rawText, err := fetcher.Fetch(bookID)
	if err != nil {
		return "", err
	}
	return lake.Store(bookID, rawText)
}

// Store splits an already fetched raw book and writes "<id>_body.txt" and
// "<id>_header.txt" (in that order, as in Python) into the layout folder.
// It returns the folder where the files were written.
func (lake Datalake) Store(bookID int, rawText string) (string, error) {
	book, err := Split(rawText)
	if err != nil {
		return "", fmt.Errorf("split book %d: %w", bookID, err)
	}
	outputDir := lake.Layout.Directory(lake.Root, bookID)
	if err := os.MkdirAll(outputDir, directoryPermissions); err != nil {
		return "", fmt.Errorf("create %s: %w", outputDir, err)
	}
	if err := writeTextFile(filepath.Join(outputDir, utils.BodyFileName(bookID)), book.Body); err != nil {
		return "", err
	}
	if err := writeTextFile(filepath.Join(outputDir, utils.HeaderFileName(bookID)), book.Header); err != nil {
		return "", err
	}
	return outputDir, nil
}

func writeTextFile(path string, content string) error {
	if err := os.WriteFile(path, []byte(content), filePermissions); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}
