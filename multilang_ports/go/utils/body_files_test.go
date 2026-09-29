package utils

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestDiscoverBookIDsReturnsSortedIDs(t *testing.T) {
	bodiesDir := t.TempDir()
	for _, name := range []string{"1342_body.txt", "11_body.txt", "84_body.txt", "11_header.txt", "notes.md"} {
		writeFile(t, filepath.Join(bodiesDir, name), "text")
	}
	bookIDs, err := DiscoverBookIDs(bodiesDir)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(bookIDs, []int{11, 84, 1342}) {
		t.Fatalf("unexpected ids %v", bookIDs)
	}
}

func TestDiscoverBookIDsRejectsInvalidIDs(t *testing.T) {
	bodiesDir := t.TempDir()
	writeFile(t, filepath.Join(bodiesDir, "draft_body.txt"), "text")
	if _, err := DiscoverBookIDs(bodiesDir); err == nil {
		t.Fatal("expected an error for a non-numeric book id")
	}
}

func TestReadBookBodyReadsTheBodyFile(t *testing.T) {
	bodiesDir := t.TempDir()
	writeFile(t, filepath.Join(bodiesDir, "84_body.txt"), "Frankenstein")
	body, err := ReadBookBody(84, bodiesDir)
	if err != nil || body != "Frankenstein" {
		t.Fatalf("unexpected body %q (err %v)", body, err)
	}
}

func writeFile(t *testing.T, path string, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}
