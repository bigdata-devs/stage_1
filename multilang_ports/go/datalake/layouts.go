package datalake

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"

	"search_engine_bench/utils"
)

// DefaultBatchSize matches the batch_size default of download_batch_based().
const DefaultBatchSize = 1000

// StoredBook holds both files of a complete book copy in a datalake.
type StoredBook struct {
	BodyPath   string
	HeaderPath string
}

// Layout decides in which directory of the datalake a book is stored.
type Layout interface {
	// Name identifies the layout in benchmark reports.
	Name() string
	// Directory returns the folder, below root, that holds the book files.
	Directory(root string, bookID int) string
	// LocateBook returns the complete copy of bookID stored below root.
	LocateBook(root string, bookID int) (StoredBook, error)
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

// LocateBook implements Layout: like find_time_based_book(), it probes the
// exact file names inside every "YYYYMMDD/HH" folder, newest first, instead
// of walking every stored file.
func (TimeBasedLayout) LocateBook(root string, bookID int) (StoredBook, error) {
	hourDirs, err := hourDirsNewestFirst(root)
	if err != nil {
		return StoredBook{}, fmt.Errorf("locate book %d: %w", bookID, err)
	}
	for _, hourDir := range hourDirs {
		if book, err := requireBook(hourDir, bookID); err == nil {
			return book, nil
		}
	}
	return StoredBook{}, fmt.Errorf("locate book %d: no complete copy below %s", bookID, root)
}

// BookBasedLayout stores books under "<root>/<BOOK_ID>/".
type BookBasedLayout struct{}

// Name implements Layout.
func (BookBasedLayout) Name() string { return "book_based" }

// Directory implements Layout.
func (BookBasedLayout) Directory(root string, bookID int) string {
	return filepath.Join(root, strconv.Itoa(bookID))
}

// LocateBook implements Layout: the folder is derived from the ID, so no
// scan is needed, like find_book_based_book().
func (layout BookBasedLayout) LocateBook(root string, bookID int) (StoredBook, error) {
	return requireBook(layout.Directory(root, bookID), bookID)
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

// LocateBook implements Layout: the range folder is derived from the ID, so
// no scan is needed, like find_batch_based_book().
func (layout BatchBasedLayout) LocateBook(root string, bookID int) (StoredBook, error) {
	return requireBook(layout.Directory(root, bookID), bookID)
}

// ListBookIDs returns the ascending IDs of every complete book below root,
// like the union of the list_*_books() helpers of the Python engine.
func ListBookIDs(root string) ([]int, error) {
	bookIDs := []int{}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), utils.BodySuffix) {
			return nil
		}
		bookID, parseErr := strconv.Atoi(strings.TrimSuffix(entry.Name(), utils.BodySuffix))
		if parseErr != nil {
			return nil
		}
		if _, statErr := os.Stat(filepath.Join(filepath.Dir(path), utils.HeaderFileName(bookID))); statErr != nil {
			return nil
		}
		bookIDs = append(bookIDs, bookID)
		return nil
	})
	if errors.Is(err, fs.ErrNotExist) {
		return []int{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("list books below %s: %w", root, err)
	}
	slices.Sort(bookIDs)
	return slices.Compact(bookIDs), nil
}

// requireBook returns the files of bookID inside dir, failing when one of
// the two files is missing.
func requireBook(dir string, bookID int) (StoredBook, error) {
	book := StoredBook{
		BodyPath:   filepath.Join(dir, utils.BodyFileName(bookID)),
		HeaderPath: filepath.Join(dir, utils.HeaderFileName(bookID)),
	}
	if _, err := os.Stat(book.BodyPath); err != nil {
		return book, fmt.Errorf("locate book %d: %w", bookID, err)
	}
	if _, err := os.Stat(book.HeaderPath); err != nil {
		return book, fmt.Errorf("locate book %d: %w", bookID, err)
	}
	return book, nil
}

// hourDirsNewestFirst lists the "<root>/YYYYMMDD/HH" folders in descending
// order, which is newest first because the names sort chronologically.
func hourDirsNewestFirst(root string) ([]string, error) {
	dateDirs, err := subdirectories(root)
	if err != nil {
		return nil, err
	}
	hourDirs := []string{}
	for _, dateDir := range dateDirs {
		hours, err := subdirectories(dateDir)
		if err != nil {
			return nil, err
		}
		hourDirs = append(hourDirs, hours...)
	}
	slices.Sort(hourDirs)
	slices.Reverse(hourDirs)
	return hourDirs, nil
}

// subdirectories returns the paths of the folders directly inside dir.
func subdirectories(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	dirs := []string{}
	for _, entry := range entries {
		if entry.IsDir() {
			dirs = append(dirs, filepath.Join(dir, entry.Name()))
		}
	}
	return dirs, nil
}

// StandardLayouts returns the three hierarchies required by Section 3.1.
func StandardLayouts() []Layout {
	return []Layout{
		TimeBasedLayout{Now: time.Now},
		BookBasedLayout{},
		BatchBasedLayout{BatchSize: DefaultBatchSize},
	}
}
