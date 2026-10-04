package benchmark

import (
	"os"
	"time"

	"search_engine_bench/datalake"
)

// resumeAfterInterruption simulates a crashed run: half of the corpus is
// considered processed, the pending books are detected, re-read and
// verified, exactly like resume_after_interruption() in Python.
func resumeAfterInterruption(layout datalake.Layout, root string, bookIDs []int) (RecoveryReport, error) {
	processed := firstIDs(bookIDs, len(bookIDs)/2)
	report := RecoveryReport{TotalBooks: len(bookIDs), ProcessedBefore: len(processed)}
	detectionStart := time.Now()
	pending, err := datalake.PendingBookIDs(root, processed)
	report.DetectionTime = time.Since(detectionStart)
	if err != nil {
		return report, err
	}
	processingStart := time.Now()
	resumed, err := readStoredBooks(layout, root, pending)
	report.ProcessingTime = time.Since(processingStart)
	if err != nil {
		return report, err
	}
	report.ProcessedAfter = len(resumed)
	report.Duplicated, report.Lost = verifyResume(bookIDs, processed, resumed)
	report.Elapsed = report.DetectionTime + report.ProcessingTime
	return report, nil
}

// readStoredBooks reads the body and header of every pending book.
func readStoredBooks(layout datalake.Layout, root string, bookIDs []int) ([]int, error) {
	resumed := make([]int, 0, len(bookIDs))
	for _, bookID := range bookIDs {
		book, err := layout.LocateBook(root, bookID)
		if err != nil {
			return nil, err
		}
		if _, err := os.ReadFile(book.BodyPath); err != nil {
			return nil, err
		}
		if _, err := os.ReadFile(book.HeaderPath); err != nil {
			return nil, err
		}
		resumed = append(resumed, bookID)
	}
	return resumed, nil
}

// verifyResume counts the resumed books that were already processed and the
// books that are missing after the resume, like verify_resume().
func verifyResume(bookIDs []int, processed []int, resumed []int) (duplicated int, lost int) {
	processedBooks := toSet(processed)
	resumedBooks := toSet(resumed)
	for _, bookID := range resumed {
		if processedBooks[bookID] {
			duplicated++
		}
	}
	for _, bookID := range bookIDs {
		if !processedBooks[bookID] && !resumedBooks[bookID] {
			lost++
		}
	}
	return duplicated, lost
}

func toSet(bookIDs []int) map[int]bool {
	set := make(map[int]bool, len(bookIDs))
	for _, bookID := range bookIDs {
		set[bookID] = true
	}
	return set
}
