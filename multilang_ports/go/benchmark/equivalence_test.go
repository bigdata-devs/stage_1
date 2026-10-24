package benchmark

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunEquivalenceWritesTheCanonicalSections(t *testing.T) {
	dir := t.TempDir()
	writeEquivalenceBody(t, dir, 1, "alpha beta alpha")
	writeEquivalenceBody(t, dir, 2, "beta gamma")
	idsPath := filepath.Join(dir, "ids.txt")
	if err := os.WriteFile(idsPath, []byte("1\n2\n"), 0644); err != nil {
		t.Fatal(err)
	}
	queriesPath := filepath.Join(dir, "queries.txt")
	if err := os.WriteFile(queriesPath, []byte("alpha beta\nbeta delta\n"), 0644); err != nil {
		t.Fatal(err)
	}
	outputPath := filepath.Join(dir, "out.txt")

	if err := RunEquivalence(dir, idsPath, queriesPath, outputPath); err != nil {
		t.Fatal(err)
	}

	content, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimRight(string(content), "\n"), "\n")
	if !strings.HasPrefix(lines[0], "tokens\t1\t") || !strings.Contains(lines[0], "\talpha\t") {
		t.Fatalf("unexpected first token line: %q", lines[0])
	}
	expectedTail := []string{
		"postings\talpha\t1",
		"postings\tbeta\t1,2",
		"postings\tgamma\t2",
		"query\t1\t1",
		"query\t2",
	}
	if len(lines) != 2+len(expectedTail) {
		t.Fatalf("unexpected line count %d: %q", len(lines), content)
	}
	for offset, expected := range expectedTail {
		if lines[2+offset] != expected {
			t.Fatalf("line %d: expected %q got %q", 2+offset, expected, lines[2+offset])
		}
	}
}

func writeEquivalenceBody(t *testing.T, dir string, bookID int, text string) {
	t.Helper()
	path := filepath.Join(dir, fmt.Sprintf("%d_body.txt", bookID))
	if err := os.WriteFile(path, []byte(text), 0644); err != nil {
		t.Fatal(err)
	}
}
