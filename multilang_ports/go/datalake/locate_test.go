package datalake

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestLocateBookUsesTheDerivedFolder(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, filepath.Join(root, "84"), "84", "header", "body")
	book, err := BookBasedLayout{}.LocateBook(root, 84)
	if err != nil {
		t.Fatal(err)
	}
	assertPath(t, book.BodyPath, filepath.Join(root, "84", "84_body.txt"))
	assertPath(t, book.HeaderPath, filepath.Join(root, "84", "84_header.txt"))
}

func TestLocateBookFailsWhenTheHeaderIsMissing(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, filepath.Join(root, "84"), "84", "header", "body")
	if err := os.Remove(filepath.Join(root, "84", "84_header.txt")); err != nil {
		t.Fatal(err)
	}
	if _, err := (BookBasedLayout{}).LocateBook(root, 84); err == nil {
		t.Fatal("expected an error for an incomplete copy")
	}
}

func TestLocateBookReturnsTheNewestTimeBasedCopy(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, filepath.Join(root, "20260930", "14"), "1342", "old", "old")
	writeStoredBook(t, filepath.Join(root, "20260930", "15"), "1342", "new", "new")
	book, err := TimeBasedLayout{}.LocateBook(root, 1342)
	if err != nil {
		t.Fatal(err)
	}
	assertPath(t, book.HeaderPath, filepath.Join(root, "20260930", "15", "1342_header.txt"))
}

func TestTimeBasedLocateSkipsNewerIncompleteCopies(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, filepath.Join(root, "20260930", "14"), "1342", "old", "old")
	writeStoredBook(t, filepath.Join(root, "20261001", "09"), "1342", "new", "new")
	if err := os.Remove(filepath.Join(root, "20261001", "09", "1342_header.txt")); err != nil {
		t.Fatal(err)
	}
	book, err := TimeBasedLayout{}.LocateBook(root, 1342)
	if err != nil {
		t.Fatal(err)
	}
	assertPath(t, book.BodyPath, filepath.Join(root, "20260930", "14", "1342_body.txt"))
}

func TestTimeBasedLocateOnlyProbesHourFolders(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, filepath.Join(root, "1342"), "1342", "h", "b")
	writeStoredBook(t, filepath.Join(root, "20260930", "14", "nested"), "1342", "h", "b")
	if _, err := (TimeBasedLayout{}).LocateBook(root, 1342); err == nil {
		t.Fatal("expected an error: no copy sits directly in a YYYYMMDD/HH folder")
	}
}

func TestListBookIDsReturnsSortedCompleteBooks(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, filepath.Join(root, "1342"), "1342", "h", "b")
	writeStoredBook(t, filepath.Join(root, "1000"), "1000", "h", "b")
	writeStoredBook(t, filepath.Join(root, "84"), "84", "h", "b")
	if err := os.Remove(filepath.Join(root, "84", "84_header.txt")); err != nil {
		t.Fatal(err)
	}
	bookIDs, err := ListBookIDs(root)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(bookIDs, []int{1000, 1342}) {
		t.Fatalf("unexpected book ids %v", bookIDs)
	}
}

func TestListBookIDsTreatsAMissingDirectoryAsEmpty(t *testing.T) {
	bookIDs, err := ListBookIDs(filepath.Join(t.TempDir(), "absent"))
	if err != nil {
		t.Fatal(err)
	}
	if len(bookIDs) != 0 {
		t.Fatalf("expected no books, got %v", bookIDs)
	}
}

func TestPendingBookIDsExcludesKnownBooks(t *testing.T) {
	root := t.TempDir()
	writeStoredBook(t, root, "1", "h", "b")
	writeStoredBook(t, root, "2", "h", "b")
	writeStoredBook(t, root, "3", "h", "b")
	pending, err := PendingBookIDs(root, []int{1, 3})
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(pending, []int{2}) {
		t.Fatalf("unexpected pending books %v", pending)
	}
}

func writeStoredBook(t *testing.T, dir string, bookID string, header string, body string) {
	t.Helper()
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	writeTextFile(filepath.Join(dir, bookID+"_header.txt"), header)
	writeTextFile(filepath.Join(dir, bookID+"_body.txt"), body)
}
