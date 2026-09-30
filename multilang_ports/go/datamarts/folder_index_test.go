package datamarts

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestSaveFolderGroupsTermsByUppercaseLetter(t *testing.T) {
	indexDir := filepath.Join(t.TempDir(), "inverted_index")
	if err := SaveFolder(sampleIndex(), indexDir); err != nil {
		t.Fatal(err)
	}
	content, err := os.ReadFile(filepath.Join(indexDir, "A", "adventure.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "5\n12\n" {
		t.Fatalf("unexpected term file %q", content)
	}
	for _, letter := range []string{"A", "I", "S"} {
		if _, err := os.Stat(filepath.Join(indexDir, letter)); err != nil {
			t.Fatalf("missing letter folder %s", letter)
		}
	}
}

func TestQueryFolderReadsOnlyTheTermFile(t *testing.T) {
	indexDir := t.TempDir()
	if err := SaveFolder(sampleIndex(), indexDir); err != nil {
		t.Fatal(err)
	}
	postings, err := QueryFolder("adventure", indexDir)
	if err != nil || !reflect.DeepEqual(postings, []int{5, 12}) {
		t.Fatalf("unexpected postings %v (err %v)", postings, err)
	}
}

func TestQueryFolderReturnsEmptyForUnknownTerm(t *testing.T) {
	indexDir := t.TempDir()
	if err := SaveFolder(sampleIndex(), indexDir); err != nil {
		t.Fatal(err)
	}
	for _, term := range []string{"ghost", ""} {
		postings, err := QueryFolder(term, indexDir)
		if err != nil || len(postings) != 0 {
			t.Fatalf("expected no postings for %q, got %v (err %v)", term, postings, err)
		}
	}
}

func TestUpdateFolderCreatesAndMergesTermFiles(t *testing.T) {
	indexDir := t.TempDir()
	if err := UpdateFolder(12, []string{"island", "ship"}, indexDir); err != nil {
		t.Fatal(err)
	}
	if err := UpdateFolder(5, []string{"island"}, indexDir); err != nil {
		t.Fatal(err)
	}
	if postings, err := QueryFolder("island", indexDir); err != nil || !reflect.DeepEqual(postings, []int{5, 12}) {
		t.Fatalf("unexpected postings %v (err %v)", postings, err)
	}
	if postings, err := QueryFolder("ship", indexDir); err != nil || !reflect.DeepEqual(postings, []int{12}) {
		t.Fatalf("unexpected postings %v (err %v)", postings, err)
	}
}
