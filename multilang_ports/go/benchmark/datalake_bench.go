package benchmark

import (
	"log"

	"search_engine_bench/datalake"
)

// rawBook is a downloaded, still unsplit Gutenberg text.
type rawBook struct {
	id   int
	text string
}

// runDatalakeBenchmark downloads every book once and then stores the same
// raw texts in each of the three hierarchies. Separating the network step
// keeps Gutenberg latency out of the per-layout write measurements, and
// avoids downloading each book three times.
func (suite Suite) runDatalakeBenchmark() error {
	books, err := suite.fetchBooksMeasured()
	if err != nil {
		return err
	}
	if len(books) == 0 {
		log.Printf("[datalake] no book could be fetched; skipping the layout benchmarks")
		return nil
	}
	for _, layout := range datalake.StandardLayouts() {
		if err := suite.benchmarkLayout(layout, books); err != nil {
			return err
		}
	}
	return nil
}

func (suite Suite) fetchBooksMeasured() ([]rawBook, error) {
	var books []rawBook
	measurement, err := suite.measure("datalake_fetch", func() error {
		books = fetchBooks(suite.fetcher(), suite.config.BookIDs)
		return nil
	})
	if err != nil || len(books) == 0 {
		return books, err
	}
	return books, suite.recordThroughput(measurement, len(books))
}

// fetchBooks mirrors download_sample_dataset(): failures are reported and
// skipped so that one missing book does not abort the whole run.
func fetchBooks(fetcher datalake.Fetcher, bookIDs []int) []rawBook {
	books := make([]rawBook, 0, len(bookIDs))
	for _, bookID := range bookIDs {
		text, err := fetcher.Fetch(bookID)
		if err != nil {
			log.Printf("[FAIL] Book %d: %v", bookID, err)
			continue
		}
		books = append(books, rawBook{id: bookID, text: text})
	}
	return books
}

// benchmarkLayout measures split + write of every book into one hierarchy.
func (suite Suite) benchmarkLayout(layout datalake.Layout, books []rawBook) error {
	lake := datalake.Datalake{Root: suite.outputPath("datalake", layout.Name()), Layout: layout}
	if err := resetDirectory(lake.Root); err != nil {
		return err
	}
	measurement, err := suite.measure("datalake_store_"+layout.Name(), func() error {
		return storeBooks(lake, books)
	})
	if err != nil {
		return err
	}
	if err := suite.recordThroughput(measurement, len(books)); err != nil {
		return err
	}
	return suite.recordDiskUsage(lake.Root)
}

func storeBooks(lake datalake.Datalake, books []rawBook) error {
	for _, book := range books {
		if _, err := lake.Store(book.id, book.text); err != nil {
			return err
		}
	}
	return nil
}
