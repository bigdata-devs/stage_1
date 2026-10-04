package datalake

import (
	"path/filepath"
	"testing"
	"time"
)

func TestTimeBasedLayoutUsesDateAndHour(t *testing.T) {
	fixedClock := func() time.Time { return time.Date(2025, 9, 25, 14, 30, 0, 0, time.Local) }
	directory := TimeBasedLayout{Now: fixedClock}.Directory("lake", 1342)
	assertPath(t, directory, filepath.Join("lake", "20250925", "14"))
}

func TestBookBasedLayoutUsesBookID(t *testing.T) {
	assertPath(t, BookBasedLayout{}.Directory("lake", 84), filepath.Join("lake", "84"))
}

func TestBatchBasedLayoutUsesInclusiveRanges(t *testing.T) {
	layout := BatchBasedLayout{BatchSize: DefaultBatchSize}
	assertPath(t, layout.Directory("lake", 1500), filepath.Join("lake", "batch_1000_1999"))
	assertPath(t, layout.Directory("lake", 999), filepath.Join("lake", "batch_0_999"))
	assertPath(t, layout.Directory("lake", 2000), filepath.Join("lake", "batch_2000_2999"))
}

func TestStandardLayoutsCoverTheThreeHierarchies(t *testing.T) {
	names := []string{}
	for _, layout := range StandardLayouts() {
		names = append(names, layout.Name())
	}
	if len(names) != 3 || names[0] != "time_based" || names[1] != "book_based" || names[2] != "batch_based" {
		t.Fatalf("unexpected layouts %v", names)
	}
}

func assertPath(t *testing.T, actual string, expected string) {
	t.Helper()
	if actual != expected {
		t.Fatalf("expected %s, got %s", expected, actual)
	}
}
