package datalake

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

// GutenbergBaseURL is the mirror used by every language port.
const GutenbergBaseURL = "https://www.gutenberg.org/cache/epub"

// downloadTimeout only protects the benchmark from hanging forever; the
// Python baseline (requests.get without timeout) has no equivalent limit.
const downloadTimeout = 60 * time.Second

// Fetcher returns the raw (unsplit) text of a Project Gutenberg book.
type Fetcher interface {
	Fetch(bookID int) (string, error)
}

// GutenbergFetcher downloads books over HTTP, one request per book, like
// requests.get() in the Python baseline.
type GutenbergFetcher struct {
	BaseURL string
	Client  *http.Client
}

// NewGutenbergFetcher returns a fetcher pointed at the official mirror.
func NewGutenbergFetcher() GutenbergFetcher {
	return GutenbergFetcher{BaseURL: GutenbergBaseURL, Client: &http.Client{Timeout: downloadTimeout}}
}

// BookURL returns "<base>/<id>/pg<id>.txt".
func (fetcher GutenbergFetcher) BookURL(bookID int) string {
	return fmt.Sprintf("%s/%d/pg%d.txt", fetcher.BaseURL, bookID, bookID)
}

// Fetch downloads a book and fails on any status other than 200 OK.
func (fetcher GutenbergFetcher) Fetch(bookID int) (string, error) {
	response, err := fetcher.Client.Get(fetcher.BookURL(bookID))
	if err != nil {
		return "", fmt.Errorf("download book %d: %w", bookID, err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return "", fmt.Errorf("download book %d: unexpected HTTP status %d", bookID, response.StatusCode)
	}
	content, err := io.ReadAll(response.Body)
	if err != nil {
		return "", fmt.Errorf("read book %d: %w", bookID, err)
	}
	return string(content), nil
}

// DirectoryFetcher reads previously downloaded raw books named
// "pg<id>.txt" from a local directory. It allows offline, network-free and
// therefore reproducible datalake benchmarks.
type DirectoryFetcher struct {
	Dir string
}

// Fetch reads "<Dir>/pg<id>.txt".
func (fetcher DirectoryFetcher) Fetch(bookID int) (string, error) {
	content, err := os.ReadFile(filepath.Join(fetcher.Dir, fmt.Sprintf("pg%d.txt", bookID)))
	if err != nil {
		return "", fmt.Errorf("read raw book %d: %w", bookID, err)
	}
	return string(content), nil
}
