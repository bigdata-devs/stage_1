package benchmark

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestLoadSharedQueriesReadsLinesAndSkipsComments(t *testing.T) {
	path := filepath.Join(t.TempDir(), "queries.txt")
	content := "# section comment\r\n\r\ntime first\r\nlet us go\r\n\r\n# another comment\r\nnonexistentterm\r\n"
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	queries, err := LoadSharedQueries(path)
	if err != nil {
		t.Fatal(err)
	}
	expected := [][]string{
		{"time", "first"},
		{"let", "us", "go"},
		{"nonexistentterm"},
	}
	if !reflect.DeepEqual(queries, expected) {
		t.Fatalf("unexpected queries: %v", queries)
	}
}

func TestLoadSharedQueriesFailsWithoutQueries(t *testing.T) {
	path := filepath.Join(t.TempDir(), "queries.txt")
	if err := os.WriteFile(path, []byte("# empty\r\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadSharedQueries(path); err == nil {
		t.Fatal("expected an error for a workload file without queries")
	}
}

func TestLoadSharedQueriesReadsRepositoryWorkloadFile(t *testing.T) {
	queries, err := LoadSharedQueries("../../../src/utils/benchmarks/queries.txt")
	if err != nil {
		t.Fatal(err)
	}
	if len(queries) != 20 {
		t.Fatalf("expected the 20 shared queries, got %d", len(queries))
	}
}

func TestIntersectPostingsKeepsDocumentsWithAllTerms(t *testing.T) {
	lookup := func(term string) ([]int, error) {
		switch term {
		case "alpha":
			return []int{5, 3, 1}, nil
		case "beta":
			return []int{1, 5}, nil
		default:
			return []int{}, nil
		}
	}
	matched, err := intersectPostings([]string{"alpha", "beta"}, lookup)
	if err != nil {
		t.Fatal(err)
	}
	if expected := []int{1, 5}; !reflect.DeepEqual(matched, expected) {
		t.Fatalf("expected %v, got %v", expected, matched)
	}
}

func TestIntersectPostingsReturnsNothingWhenATermIsMissing(t *testing.T) {
	lookup := func(term string) ([]int, error) {
		if term == "alpha" {
			return []int{1, 2}, nil
		}
		return []int{}, nil
	}
	matched, err := intersectPostings([]string{"alpha", "missing"}, lookup)
	if err != nil {
		t.Fatal(err)
	}
	if len(matched) != 0 {
		t.Fatalf("expected no documents, got %v", matched)
	}
}
