package datalake

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestDownloadStoresBodyAndHeader(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/1342/pg1342.txt" {
			http.NotFound(writer, request)
			return
		}
		writer.Write([]byte(sampleText))
	}))
	defer server.Close()
	fetcher := GutenbergFetcher{BaseURL: server.URL, Client: server.Client()}
	lake := Datalake{Root: t.TempDir(), Layout: BookBasedLayout{}}

	outputDir, err := lake.Download(fetcher, 1342)
	if err != nil {
		t.Fatal(err)
	}
	assertFileContent(t, filepath.Join(outputDir, "1342_header.txt"), sampleHeader)
	assertFileContent(t, filepath.Join(outputDir, "1342_body.txt"), "SAMPLE ***\n"+sampleBody)
}

func TestDownloadFailsOnHTTPError(t *testing.T) {
	server := httptest.NewServer(http.NotFoundHandler())
	defer server.Close()
	fetcher := GutenbergFetcher{BaseURL: server.URL, Client: server.Client()}
	lake := Datalake{Root: t.TempDir(), Layout: BookBasedLayout{}}
	if _, err := lake.Download(fetcher, 1); err == nil {
		t.Fatal("expected an error for HTTP 404")
	}
}

func TestStoreRejectsBooksWithoutMarkersAndWritesNothing(t *testing.T) {
	root := t.TempDir()
	lake := Datalake{Root: root, Layout: BatchBasedLayout{BatchSize: DefaultBatchSize}}
	if _, err := lake.Store(7, "plain text"); err == nil {
		t.Fatal("expected an error")
	}
	if entries, _ := os.ReadDir(root); len(entries) != 0 {
		t.Fatalf("expected an empty datalake, found %d entries", len(entries))
	}
}

func TestDirectoryFetcherReadsRawBooks(t *testing.T) {
	rawDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(rawDir, "pg11.txt"), []byte(sampleText), 0o644); err != nil {
		t.Fatal(err)
	}
	text, err := DirectoryFetcher{Dir: rawDir}.Fetch(11)
	if err != nil || text != sampleText {
		t.Fatalf("unexpected fetch result (err %v)", err)
	}
}

func TestBookURLMatchesGutenbergPattern(t *testing.T) {
	url := NewGutenbergFetcher().BookURL(84)
	if url != "https://www.gutenberg.org/cache/epub/84/pg84.txt" {
		t.Fatalf("unexpected url %s", url)
	}
}

func assertFileContent(t *testing.T, path string, expected string) {
	t.Helper()
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != expected {
		t.Fatalf("%s: expected %q, got %q", path, expected, content)
	}
}
