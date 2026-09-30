package benchmark

import (
	"context"
	"log"
	"time"

	"search_engine_bench/datamarts"
)

// runIndexBenchmark measures, for every index structure, the end-to-end
// build (discover + read + tokenize + build postings + persist) and then the
// shared query workload. The end-to-end build matches what the
// `build` command of the Rust, Java and C ports does in a single run.
func (suite Suite) runIndexBenchmark() error {
	bookCount, err := suite.measurePipelineStages()
	if err != nil {
		return err
	}
	if err := suite.benchmarkJSONIndex(bookCount); err != nil {
		return err
	}
	if err := suite.benchmarkFolderIndex(bookCount); err != nil {
		return err
	}
	return suite.benchmarkMongoIndex(bookCount)
}

// measurePipelineStages times tokenization and postings construction alone,
// so the cost of persisting each structure can be isolated in the report.
func (suite Suite) measurePipelineStages() (int, error) {
	var books []datamarts.TokenizedBook
	tokenizeMeasurement, err := suite.measure("index_tokenize", func() error {
		var loadErr error
		books, loadErr = datamarts.LoadTokenizedBooks(suite.config.BodiesDir)
		return loadErr
	})
	if err != nil {
		return 0, err
	}
	log.Printf("[index] %d books from %s", len(books), suite.config.BodiesDir)
	if err := suite.recordThroughput(tokenizeMeasurement, len(books)); err != nil {
		return 0, err
	}
	var index datamarts.InvertedIndex
	_, err = suite.measure("index_build_postings", func() error {
		index = datamarts.BuildPostings(books)
		return nil
	})
	log.Printf("[index] %d unique terms", index.TermCount())
	return len(books), err
}

// buildAndPersist is the end-to-end pipeline shared by every structure.
func (suite Suite) buildAndPersist(persist func(datamarts.InvertedIndex) error) func() error {
	return func() error {
		books, err := datamarts.LoadTokenizedBooks(suite.config.BodiesDir)
		if err != nil {
			return err
		}
		return persist(datamarts.BuildPostings(books))
	}
}

func (suite Suite) benchmarkJSONIndex(bookCount int) error {
	indexPath := suite.outputPath("datamarts", "inverted_index.json")
	measurement, err := suite.measure("index_json_build", suite.buildAndPersist(func(index datamarts.InvertedIndex) error {
		return datamarts.SaveJSON(index, indexPath)
	}))
	if err != nil {
		return err
	}
	if err := suite.recordThroughput(measurement, bookCount); err != nil {
		return err
	}
	if err := suite.recordDiskUsage(indexPath); err != nil {
		return err
	}
	return suite.benchmarkJSONQueries(indexPath)
}

// benchmarkJSONQueries loads the file once (measured separately, as it is the
// dominant cost of this structure) and then times in-memory lookups.
func (suite Suite) benchmarkJSONQueries(indexPath string) error {
	var loaded map[string][]int
	if _, err := suite.measure("index_json_load", func() error {
		var loadErr error
		loaded, loadErr = datamarts.LoadJSON(indexPath)
		return loadErr
	}); err != nil {
		return err
	}
	durations, err := suite.runQueryWorkload(func(term string) error {
		_ = loaded[term]
		return nil
	})
	if err != nil {
		return err
	}
	return suite.recordQueryStatistics("query_json", durations)
}

func (suite Suite) benchmarkFolderIndex(bookCount int) error {
	indexDir := suite.outputPath("datamarts", "inverted_index")
	if err := resetDirectory(indexDir); err != nil {
		return err
	}
	measurement, err := suite.measure("index_folder_build", suite.buildAndPersist(func(index datamarts.InvertedIndex) error {
		return datamarts.SaveFolder(index, indexDir)
	}))
	if err != nil {
		return err
	}
	if err := suite.recordThroughput(measurement, bookCount); err != nil {
		return err
	}
	if err := suite.recordDiskUsage(indexDir); err != nil {
		return err
	}
	durations, err := suite.runQueryWorkload(func(term string) error {
		_, queryErr := datamarts.QueryFolder(term, indexDir)
		return queryErr
	})
	if err != nil {
		return err
	}
	return suite.recordQueryStatistics("query_folder", durations)
}

func (suite Suite) benchmarkMongoIndex(bookCount int) error {
	ctx := context.Background()
	if suite.config.SkipMongo || !datamarts.IsMongoAvailable(ctx, suite.config.MongoURI) {
		log.Printf("[mongo] MongoDB skipped (disabled or not reachable at %s)", suite.config.MongoURI)
		return nil
	}
	mongoIndex, err := suite.connectMongo(ctx)
	if err != nil {
		return err
	}
	defer mongoIndex.Close(ctx)
	measurement, err := suite.measure("index_mongo_build", suite.buildAndPersist(func(index datamarts.InvertedIndex) error {
		return mongoIndex.Save(ctx, index)
	}))
	if err != nil {
		return err
	}
	if err := suite.recordThroughput(measurement, bookCount); err != nil {
		return err
	}
	if err := suite.recordMongoStorage(ctx, mongoIndex); err != nil {
		return err
	}
	durations, err := suite.runQueryWorkload(func(term string) error {
		_, queryErr := mongoIndex.Query(ctx, term)
		return queryErr
	})
	if err != nil {
		return err
	}
	return suite.recordQueryStatistics("query_mongo", durations)
}

// recordMongoStorage writes a disk_usage.csv row for the collection: size is
// storageSize + totalIndexSize and file_count is the number of documents.
func (suite Suite) recordMongoStorage(ctx context.Context, mongoIndex *datamarts.MongoIndex) error {
	stats, err := mongoIndex.StorageStats(ctx)
	if err != nil {
		return err
	}
	usage := DiskUsage{
		Path:      suite.config.MongoURI + "/" + suite.config.MongoDatabase + "." + suite.config.MongoCollection,
		SizeMB:    toMB(stats.StorageBytes + stats.IndexBytes),
		FileCount: int(stats.Documents),
	}
	log.Printf("[disk] %s: %.4f MB (data %.4f MB), %d documents",
		usage.Path, usage.SizeMB, toMB(stats.DataBytes), stats.Documents)
	return suite.results.SaveDiskUsage(usage)
}

// runQueryWorkload times every query term QueryRepetitions times, one at a
// time, and returns the individual latencies.
func (suite Suite) runQueryWorkload(query func(term string) error) ([]time.Duration, error) {
	durations := make([]time.Duration, 0, len(suite.config.QueryTerms)*suite.config.QueryRepetitions)
	for repetition := 0; repetition < suite.config.QueryRepetitions; repetition++ {
		for _, term := range suite.config.QueryTerms {
			start := time.Now()
			if err := query(term); err != nil {
				return nil, err
			}
			durations = append(durations, time.Since(start))
		}
	}
	return durations, nil
}
