package benchmark

import (
	"reflect"
	"testing"

	"search_engine_bench/datamarts"
)

func TestBuildBatchSizesMergesCorpusSizeIntoThePythonList(t *testing.T) {
	if sizes := buildBatchSizes(100); !reflect.DeepEqual(sizes, []int{10, 25, 50, 100, 250, 500}) {
		t.Fatalf("unexpected batch sizes %v", sizes)
	}
	if sizes := buildBatchSizes(250); !reflect.DeepEqual(sizes, []int{10, 25, 50, 250, 500}) {
		t.Fatalf("unexpected batch sizes %v", sizes)
	}
}

func TestBuildSubsetKeepsRealBooksAndAddsSyntheticOnes(t *testing.T) {
	books := []datamarts.TokenizedBook{
		{ID: 11, Tokens: []string{"cat"}},
		{ID: 84, Tokens: []string{"dog"}},
		{ID: 1342, Tokens: []string{"fox"}},
	}
	onlyReal := buildSubset(books, 2)
	if len(onlyReal) != 2 || onlyReal[1].ID != 84 {
		t.Fatalf("unexpected subset %+v", onlyReal)
	}
	withSynthetic := buildSubset(books, 5)
	expectedIDs := []int{11, 84, 1342, 900000, 900001}
	gotIDs := make([]int, len(withSynthetic))
	for position, book := range withSynthetic {
		gotIDs[position] = book.ID
	}
	if !reflect.DeepEqual(gotIDs, expectedIDs) {
		t.Fatalf("unexpected ids %v", gotIDs)
	}
	if !reflect.DeepEqual(withSynthetic[3].Tokens, []string{"cat"}) ||
		!reflect.DeepEqual(withSynthetic[4].Tokens, []string{"dog"}) {
		t.Fatalf("unexpected synthetic tokens %+v", withSynthetic[3:])
	}
}
