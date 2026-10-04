package datamarts

import (
	"reflect"
	"testing"
)

func TestBuildPostingsSingleBook(t *testing.T) {
	index := BuildPostings([]TokenizedBook{{ID: 1, Tokens: []string{"cat", "dog", "cat"}}})
	assertIndex(t, index, map[string][]int{"cat": {1}, "dog": {1}})
}

func TestBuildPostingsMultipleBooks(t *testing.T) {
	index := BuildPostings([]TokenizedBook{
		{ID: 1, Tokens: []string{"cat", "dog"}},
		{ID: 2, Tokens: []string{"dog", "bird"}},
	})
	assertIndex(t, index, map[string][]int{"cat": {1}, "dog": {1, 2}, "bird": {2}})
}

func TestBuildPostingsSortsAndDeduplicatesLikeSortedSet(t *testing.T) {
	index := BuildPostings([]TokenizedBook{
		{ID: 9, Tokens: []string{"cat"}},
		{ID: 3, Tokens: []string{"cat"}},
		{ID: 9, Tokens: []string{"cat"}},
	})
	assertIndex(t, index, map[string][]int{"cat": {3, 9}})
}

func TestBuildPostingsKeepsFirstAppearanceOrder(t *testing.T) {
	index := BuildPostings([]TokenizedBook{
		{ID: 1, Tokens: []string{"zebra", "apple"}},
		{ID: 2, Tokens: []string{"mango", "apple"}},
	})
	terms := []string{}
	for _, entry := range index.Entries() {
		terms = append(terms, entry.Term)
	}
	if !reflect.DeepEqual(terms, []string{"zebra", "apple", "mango"}) {
		t.Fatalf("unexpected term order %v", terms)
	}
}

func TestPostingsOfUnknownTermIsEmpty(t *testing.T) {
	index := BuildPostings(nil)
	if postings := index.Postings("ghost"); len(postings) != 0 {
		t.Fatalf("expected no postings, got %v", postings)
	}
}

func TestFormatPostingsMatchesOtherPorts(t *testing.T) {
	if formatted := FormatPostings([]int{11, 84, 1342}); formatted != "[11, 84, 1342]" {
		t.Fatalf("unexpected format %s", formatted)
	}
	if formatted := FormatPostings(nil); formatted != "[]" {
		t.Fatalf("unexpected format %s", formatted)
	}
}

func assertIndex(t *testing.T, index InvertedIndex, expected map[string][]int) {
	t.Helper()
	actual := make(map[string][]int, index.TermCount())
	for _, entry := range index.Entries() {
		actual[entry.Term] = entry.Postings
	}
	if !reflect.DeepEqual(actual, expected) {
		t.Fatalf("expected %v, got %v", expected, actual)
	}
}

func TestUniqueTermsKeepsFirstAppearance(t *testing.T) {
	terms := UniqueTerms([]string{"cat", "dog", "cat", "bird", "dog"})
	if !reflect.DeepEqual(terms, []string{"cat", "dog", "bird"}) {
		t.Fatalf("unexpected terms %v", terms)
	}
}

func TestAppendSortedUniqueInsertsInOrder(t *testing.T) {
	postings := AppendSortedUnique([]int{5, 12}, 9)
	if !reflect.DeepEqual(postings, []int{5, 9, 12}) {
		t.Fatalf("unexpected postings %v", postings)
	}
	if postings := AppendSortedUnique([]int{5, 12}, 5); !reflect.DeepEqual(postings, []int{5, 12}) {
		t.Fatalf("expected no duplicate, got %v", postings)
	}
	if postings := AppendSortedUnique(nil, 7); !reflect.DeepEqual(postings, []int{7}) {
		t.Fatalf("unexpected postings %v", postings)
	}
}
