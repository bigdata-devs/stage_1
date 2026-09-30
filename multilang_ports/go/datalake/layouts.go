package datalake

import (
	"fmt"
	"path/filepath"
	"strconv"
	"time"
)

// DefaultBatchSize matches the batch_size default of download_batch_based().
const DefaultBatchSize = 1000

// Layout decides in which directory of the datalake a book is stored.
type Layout interface {
	// Name identifies the layout in benchmark reports.
	Name() string
	// Directory returns the folder, below root, that holds the book files.
	Directory(root string, bookID int) string
}

// TimeBasedLayout stores books under "<root>/YYYYMMDD/HH/", using the moment
// each book is written (datetime.now() in download_time_based()).
type TimeBasedLayout struct {
	Now func() time.Time
}

// Name implements Layout.
func (TimeBasedLayout) Name() string { return "time_based" }

// Directory implements Layout.
func (layout TimeBasedLayout) Directory(root string, _ int) string {
	now := layout.Now()
	return filepath.Join(root, now.Format("20060102"), now.Format("15"))
}

// BookBasedLayout stores books under "<root>/<BOOK_ID>/".
type BookBasedLayout struct{}

// Name implements Layout.
func (BookBasedLayout) Name() string { return "book_based" }

// Directory implements Layout.
func (BookBasedLayout) Directory(root string, bookID int) string {
	return filepath.Join(root, strconv.Itoa(bookID))
}

// BatchBasedLayout stores books under "<root>/batch_<lower>_<upper>/",
// e.g. book 1342 with a batch size of 1000 goes to "batch_1000_1999".
type BatchBasedLayout struct {
	BatchSize int
}

// Name implements Layout.
func (BatchBasedLayout) Name() string { return "batch_based" }

// Directory implements Layout.
func (layout BatchBasedLayout) Directory(root string, bookID int) string {
	lowerBound := (bookID / layout.BatchSize) * layout.BatchSize
	upperBound := lowerBound + layout.BatchSize - 1
	return filepath.Join(root, fmt.Sprintf("batch_%d_%d", lowerBound, upperBound))
}

// StandardLayouts returns the three hierarchies required by Section 3.1.
func StandardLayouts() []Layout {
	return []Layout{
		TimeBasedLayout{Now: time.Now},
		BookBasedLayout{},
		BatchBasedLayout{BatchSize: DefaultBatchSize},
	}
}
