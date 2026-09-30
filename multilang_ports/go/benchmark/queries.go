package benchmark

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strings"
)

// LoadSharedQueries reads the shared workload file: one query per line with
// its terms separated by spaces and '#' introducing a comment. Section 4.2
// requires every language to run exactly these queries with the intersection
// semantics of intersectPostings.
func LoadSharedQueries(path string) ([][]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open queries file: %w", err)
	}
	defer file.Close()
	var queries [][]string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		terms := termsOf(scanner.Text())
		if len(terms) > 0 {
			queries = append(queries, terms)
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("read queries file: %w", err)
	}
	if len(queries) == 0 {
		return nil, fmt.Errorf("%s must define at least one query", path)
	}
	return queries, nil
}

func termsOf(line string) []string {
	if comment := strings.IndexByte(line, '#'); comment >= 0 {
		line = line[:comment]
	}
	return strings.Fields(line)
}

// intersectPostings returns the sorted book IDs present in the postings of
// every term, so a query matches a document only if it contains all its terms.
func intersectPostings(terms []string, lookup func(term string) ([]int, error)) ([]int, error) {
	var matched map[int]bool
	for position, term := range terms {
		postings, err := lookup(term)
		if err != nil {
			return nil, err
		}
		current := make(map[int]bool, len(postings))
		for _, bookID := range postings {
			current[bookID] = true
		}
		if position == 0 {
			matched = current
		} else {
			for bookID := range matched {
				if !current[bookID] {
					delete(matched, bookID)
				}
			}
		}
		if len(matched) == 0 {
			break
		}
	}
	result := make([]int, 0, len(matched))
	for bookID := range matched {
		result = append(result, bookID)
	}
	sort.Ints(result)
	return result, nil
}
