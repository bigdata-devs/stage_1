package benchmark

import (
	"testing"

	"search_engine_bench/datalake"
)

func TestFirstIDsReturnsTheLeadingSlice(t *testing.T) {
	ids := []int{1, 2, 3, 4}
	if got := firstIDs(ids, 2); len(got) != 2 || got[1] != 2 {
		t.Fatalf("unexpected ids %v", got)
	}
	if got := firstIDs(ids, 10); len(got) != 4 {
		t.Fatalf("expected all ids, got %v", got)
	}
}

func TestVerifyResumeCountsDuplicatesAndLostBooks(t *testing.T) {
	duplicated, lost := verifyResume([]int{1, 2, 3, 4}, []int{1, 2}, []int{2, 3})
	if duplicated != 1 || lost != 1 {
		t.Fatalf("expected duplicated=1 (book 2) and lost=1 (book 4), got %d and %d", duplicated, lost)
	}
}

func TestResumeAfterInterruptionResumesThePendingHalf(t *testing.T) {
	root := t.TempDir()
	layout := datalake.BookBasedLayout{}
	bookIDs := []int{10, 20, 30, 40}
	for _, bookID := range bookIDs {
		writeStoredBookForBenchmark(t, layout, root, bookID)
	}
	report, err := resumeAfterInterruption(layout, root, bookIDs)
	if err != nil {
		t.Fatal(err)
	}
	if report.TotalBooks != 4 || report.ProcessedBefore != 2 || report.ProcessedAfter != 2 {
		t.Fatalf("unexpected report %+v", report)
	}
	if report.Duplicated != 0 || report.Lost != 0 {
		t.Fatalf("expected a clean resume, got %d duplicated and %d lost", report.Duplicated, report.Lost)
	}
	if report.Elapsed <= 0 || report.DetectionTime <= 0 || report.ProcessingTime <= 0 {
		t.Fatalf("expected positive timings, got %+v", report)
	}
}

func writeStoredBookForBenchmark(t *testing.T, layout datalake.Layout, root string, bookID int) {
	t.Helper()
	lake := datalake.Datalake{Root: root, Layout: layout}
	if _, err := lake.StoreBook(bookID, "header", "body"); err != nil {
		t.Fatal(err)
	}
}
