package datamarts

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func sampleIndex() InvertedIndex {
	return BuildPostings([]TokenizedBook{
		{ID: 5, Tokens: []string{"adventure", "island"}},
		{ID: 12, Tokens: []string{"adventure", "shipwreck"}},
	})
}

func TestSaveJSONMatchesPythonJSONDumpIndent2(t *testing.T) {
	indexPath := filepath.Join(t.TempDir(), "nested", "inverted_index.json")
	if err := SaveJSON(sampleIndex(), indexPath); err != nil {
		t.Fatal(err)
	}
	content, _ := os.ReadFile(indexPath)
	// json.dump({"adventure": [5, 12], "island": [5], "shipwreck": [12]}, f, ensure_ascii=False, indent=2)
	expected := "{\n  \"adventure\": [\n    5,\n    12\n  ],\n  \"island\": [\n    5\n  ],\n  \"shipwreck\": [\n    12\n  ]\n}"
	if string(content) != expected {
		t.Fatalf("unexpected JSON:\n%s", content)
	}
}

func TestSaveJSONWritesEmptyObjectForEmptyIndex(t *testing.T) {
	indexPath := filepath.Join(t.TempDir(), "empty.json")
	if err := SaveJSON(BuildPostings(nil), indexPath); err != nil {
		t.Fatal(err)
	}
	if content, _ := os.ReadFile(indexPath); string(content) != "{}" {
		t.Fatalf("unexpected JSON %q", content)
	}
}

func TestLoadJSONRoundTrip(t *testing.T) {
	indexPath := filepath.Join(t.TempDir(), "inverted_index.json")
	if err := SaveJSON(sampleIndex(), indexPath); err != nil {
		t.Fatal(err)
	}
	loaded, err := LoadJSON(indexPath)
	if err != nil {
		t.Fatal(err)
	}
	expected := map[string][]int{"adventure": {5, 12}, "island": {5}, "shipwreck": {12}}
	if !reflect.DeepEqual(loaded, expected) {
		t.Fatalf("expected %v, got %v", expected, loaded)
	}
}
