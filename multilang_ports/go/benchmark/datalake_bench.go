package benchmark

import (
	"log"
	"time"

	"search_engine_bench/datalake"
	"search_engine_bench/utils"
)

// downloadProbeCount is the number of books the download benchmark fetches,
// matching DOWNLOAD_PROBE_COUNT in the Python suite.
const downloadProbeCount = 10

// runDatalakeBenchmark fills every hierarchy from the tracked corpus and
// measures write, lookup, incremental detection, recovery and disk usage per
// layout; the network download benchmark runs last so that Gutenberg
// latency never contaminates the local measurements.
func (suite Suite) runDatalakeBenchmark() error {
	for _, layout := range datalake.StandardLayouts() {
		if err := suite.benchmarkLayout(layout); err != nil {
			return err
		}
	}
	return suite.measureDownloadProbe()
}

func (suite Suite) benchmarkLayout(layout datalake.Layout) error {
	lake := datalake.Datalake{Root: suite.outputPath("datalake", layout.Name()), Layout: layout}
	if err := resetDirectory(lake.Root); err != nil {
		return err
	}
	if err := suite.measureLayoutWrite(lake); err != nil {
		return err
	}
	if err := suite.measureLayoutLookup(layout, lake); err != nil {
		return err
	}
	if err := suite.measureLayoutIncremental(lake); err != nil {
		return err
	}
	if err := suite.measureLayoutRecovery(layout, lake); err != nil {
		return err
	}
	return suite.recordDiskUsage(lake.Root)
}

// measureLayoutWrite stores every tracked header and body in one layout.
func (suite Suite) measureLayoutWrite(lake datalake.Datalake) error {
	measurement, err := suite.measure("write_throughput_"+lake.Layout.Name(), func() error {
		return suite.populateFromCorpus(lake)
	})
	if err != nil {
		return err
	}
	return suite.recordThroughput(measurement, len(suite.config.BookIDs))
}

// populateFromCorpus reads the tracked corpus and writes it into the lake.
func (suite Suite) populateFromCorpus(lake datalake.Datalake) error {
	for _, bookID := range suite.config.BookIDs {
		body, err := utils.ReadBookBody(bookID, suite.config.BodiesDir)
		if err != nil {
			return err
		}
		header, err := utils.ReadBookHeader(bookID, suite.config.HeadersDir)
		if err != nil {
			return err
		}
		if _, err := lake.StoreBook(bookID, header, body); err != nil {
			return err
		}
	}
	return nil
}

// measureLayoutLookup times locating every stored book once, like measure_lookup().
func (suite Suite) measureLayoutLookup(layout datalake.Layout, lake datalake.Datalake) error {
	durations := make([]time.Duration, 0, len(suite.config.BookIDs))
	for _, bookID := range suite.config.BookIDs {
		start := time.Now()
		if _, err := layout.LocateBook(lake.Root, bookID); err != nil {
			return err
		}
		durations = append(durations, time.Since(start))
	}
	return suite.recordQueryStatistics("lookup_"+layout.Name(), durations)
}

// measureLayoutIncremental times the pending scan when half the corpus is known.
func (suite Suite) measureLayoutIncremental(lake datalake.Datalake) error {
	known := firstIDs(suite.config.BookIDs, len(suite.config.BookIDs)/2)
	_, err := suite.measure("incremental_"+lake.Layout.Name(), func() error {
		_, pendingErr := datalake.PendingBookIDs(lake.Root, known)
		return pendingErr
	})
	return err
}

// measureLayoutRecovery resumes an interrupted run and stores recovery.csv.
func (suite Suite) measureLayoutRecovery(layout datalake.Layout, lake datalake.Datalake) error {
	report, err := resumeAfterInterruption(layout, lake.Root, suite.config.BookIDs)
	if err != nil {
		return err
	}
	log.Printf("[recovery_%s] %d resumed, %d duplicated, %d lost", layout.Name(),
		report.ProcessedAfter, report.Duplicated, report.Lost)
	return suite.results.SaveRecovery("recovery_"+layout.Name(), report)
}

// measureDownloadProbe downloads a fresh sample of the corpus and stores
// throughput rows only when at least one book could be fetched; a fully
// offline run is skipped, as in the Python suite.
func (suite Suite) measureDownloadProbe() error {
	probeIDs := firstIDs(suite.config.BookIDs, downloadProbeCount)
	if len(probeIDs) == 0 {
		return nil
	}
	probeRoot := suite.outputPath("datalake", "download_probe")
	if err := resetDirectory(probeRoot); err != nil {
		return err
	}
	stored := 0
	measurement, err := Measure("download_write_throughput", func() error {
		stored = downloadProbe(suite.fetcher(), probeIDs, probeRoot)
		return nil
	})
	if err != nil {
		return err
	}
	if stored == 0 {
		log.Printf("[datalake] SKIP download_write_throughput: network unavailable")
		return nil
	}
	if err := suite.saveMeasurement(measurement); err != nil {
		return err
	}
	return suite.recordThroughput(measurement, stored)
}

// downloadProbe fetches every probe book into a fresh time-based folder and
// returns how many books were stored.
func downloadProbe(fetcher datalake.Fetcher, probeIDs []int, probeRoot string) int {
	lake := datalake.Datalake{Root: probeRoot, Layout: datalake.TimeBasedLayout{Now: time.Now}}
	stored := 0
	for _, bookID := range probeIDs {
		if _, err := lake.Download(fetcher, bookID); err != nil {
			log.Printf("[FAIL] Book %d: %v", bookID, err)
			continue
		}
		stored++
	}
	return stored
}
