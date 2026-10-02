package benchmark

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"log"
	"os"
	"slices"
	"time"

	"search_engine_bench/datamarts"
)

// syntheticBookIDBase is the ID of the first synthetic book, matching
// SYNTHETIC_BOOK_ID_BASE in the Python suite.
const syntheticBookIDBase = 900000

// indexStructure is one persistent inverted index with the five experiment
// phases of run_structure_experiments().
type indexStructure interface {
	name() string
	reset() error
	build(books []datamarts.TokenizedBook) error
	prepareQuery() error
	queryPostings(term string) ([]int, error)
	addBook(bookID int, tokens []string) error
	storageUsage() (DiskUsage, error)
	close() error
}

// runIndexBenchmark measures tokenization and postings construction once and
// then runs every structure through the scalability builds, the shared query
// workload, a book update and the storage overhead, in the Python order.
func (suite Suite) runIndexBenchmark() error {
	books, err := suite.measurePipelineStages()
	if err != nil {
		return err
	}
	if len(books) == 0 {
		return fmt.Errorf("index benchmark: no books in %s", suite.config.BodiesDir)
	}
	ctx := context.Background()
	structures, err := suite.indexStructures(ctx)
	if err != nil {
		return err
	}
	defer closeStructures(structures)
	for _, structure := range structures {
		if err := suite.runStructureExperiments(structure, books); err != nil {
			return fmt.Errorf("%s experiments: %w", structure.name(), err)
		}
	}
	return nil
}

// runStructureExperiments mirrors run_structure_experiments(): reset,
// scalability builds, query workload, book update, storage overhead.
func (suite Suite) runStructureExperiments(structure indexStructure, books []datamarts.TokenizedBook) error {
	log.Printf("--- Inverted index structure: %s ---", structure.name())
	if err := structure.reset(); err != nil {
		return err
	}
	for _, batchSize := range buildBatchSizes(len(books)) {
		batch := buildSubset(books, batchSize)
		if err := suite.measureBuildBatch(structure, batch, batchSize); err != nil {
			return err
		}
	}
	if err := structure.prepareQuery(); err != nil {
		return err
	}
	if err := suite.measureStructureQuery(structure); err != nil {
		return err
	}
	if err := suite.measureStructureUpdate(structure, books); err != nil {
		return err
	}
	return suite.measureStructureStorage(structure)
}

// measureBuildBatch stores one scalability.csv row per batch size, the only
// output of measure_build() in the Python suite.
func (suite Suite) measureBuildBatch(structure indexStructure, batch []datamarts.TokenizedBook, batchSize int) error {
	measurement, err := Measure("build_"+structure.name(), func() error {
		return structure.build(batch)
	})
	if err != nil {
		return err
	}
	log.Printf("[build_%s] batch %d: %.4fs", structure.name(), batchSize, measurement.Elapsed.Seconds())
	return suite.results.SaveScalability("build_"+structure.name(), batchSize, measurement)
}

// measureStructureQuery times the shared workload against one structure.
func (suite Suite) measureStructureQuery(structure indexStructure) error {
	durations, err := suite.runQueryWorkload(structure.queryPostings)
	if err != nil {
		return err
	}
	return suite.recordQueryStatistics("query_"+structure.name(), durations)
}

// measureStructureUpdate inserts a book built like measure_update(): the new
// ID is max + 1 and the tokens are those of the first corpus book.
func (suite Suite) measureStructureUpdate(structure indexStructure, books []datamarts.TokenizedBook) error {
	newBookID := books[len(books)-1].ID + 1
	_, err := suite.measure("update_"+structure.name(), func() error {
		return structure.addBook(newBookID, books[0].Tokens)
	})
	return err
}

// measureStructureStorage writes the disk_usage.csv row of one structure.
func (suite Suite) measureStructureStorage(structure indexStructure) error {
	usage, err := structure.storageUsage()
	if err != nil {
		return err
	}
	log.Printf("[disk] %s: %.4f MB, %d files, %d dirs", usage.Path, usage.SizeMB, usage.FileCount, usage.DirCount)
	return suite.results.SaveDiskUsage(usage)
}

// indexStructures returns the structures to benchmark; MongoDB joins the
// list only when it is enabled and reachable, like create_mongo_structure().
func (suite Suite) indexStructures(ctx context.Context) ([]indexStructure, error) {
	structures := []indexStructure{
		&jsonIndexStructure{suite: suite},
		&folderIndexStructure{suite: suite},
	}
	if suite.config.SkipMongo || !datamarts.IsMongoAvailable(ctx, suite.config.MongoURI) {
		log.Printf("[mongo] MongoDB skipped (disabled or not reachable at %s)", suite.config.MongoURI)
		return structures, nil
	}
	mongoIndex, err := suite.connectMongo(ctx)
	if err != nil {
		return nil, err
	}
	return append(structures, &mongoIndexStructure{suite: suite, index: mongoIndex, ctx: ctx}), nil
}

func closeStructures(structures []indexStructure) {
	for _, structure := range structures {
		if err := structure.close(); err != nil {
			log.Printf("[index] close %s: %v", structure.name(), err)
		}
	}
}

// buildBatchSizes returns the fixed Python batch sizes plus the corpus size.
func buildBatchSizes(bookCount int) []int {
	sizes := []int{25, 50, 250, 500, 1000, 5000, 10000, bookCount}
	slices.Sort(sizes)
	return slices.Compact(sizes)
}

// buildSubset mirrors build_subset(): the first batchSize real books topped
// up with synthetic books whose IDs start at syntheticBookIDBase and whose
// tokens cycle through the corpus.
func buildSubset(books []datamarts.TokenizedBook, batchSize int) []datamarts.TokenizedBook {
	realCount := min(batchSize, len(books))
	subset := make([]datamarts.TokenizedBook, 0, batchSize)
	subset = append(subset, books[:realCount]...)
	for offset := 0; offset < batchSize-realCount; offset++ {
		subset = append(subset, datamarts.TokenizedBook{
			ID:     syntheticBookIDBase + offset,
			Tokens: books[offset%len(books)].Tokens,
		})
	}
	return subset
}

// measurePipelineStages times tokenization and postings construction alone,
// so the cost of persisting each structure can be isolated in the report.
func (suite Suite) measurePipelineStages() ([]datamarts.TokenizedBook, error) {
	var books []datamarts.TokenizedBook
	tokenizeMeasurement, err := suite.measure("tokenize_books", func() error {
		var loadErr error
		books, loadErr = datamarts.LoadTokenizedBooks(suite.config.BodiesDir)
		return loadErr
	})
	if err != nil {
		return nil, err
	}
	log.Printf("[index] %d books from %s", len(books), suite.config.BodiesDir)
	if err := suite.recordThroughput(tokenizeMeasurement, len(books)); err != nil {
		return nil, err
	}
	var index datamarts.InvertedIndex
	if _, err := suite.measure("build_postings", func() error {
		index = datamarts.BuildPostings(books)
		return nil
	}); err != nil {
		return nil, err
	}
	log.Printf("[index] %d unique terms", index.TermCount())
	return books, nil
}

// jsonIndexStructure runs the experiments on the monolithic JSON file.
type jsonIndexStructure struct {
	suite  Suite
	loaded map[string][]int
}

func (structure *jsonIndexStructure) name() string { return "json_index" }

func (structure *jsonIndexStructure) path() string {
	return structure.suite.outputPath("datamarts", "inverted_index.json")
}

func (structure *jsonIndexStructure) reset() error {
	structure.loaded = map[string][]int{}
	err := os.Remove(structure.path())
	if errors.Is(err, fs.ErrNotExist) {
		return nil
	}
	return err
}

func (structure *jsonIndexStructure) build(books []datamarts.TokenizedBook) error {
	return datamarts.SaveJSON(datamarts.BuildPostings(books), structure.path())
}

func (structure *jsonIndexStructure) prepareQuery() error {
	var loadErr error
	_, err := structure.suite.measure("load_json_index", func() error {
		structure.loaded, loadErr = datamarts.LoadJSON(structure.path())
		return loadErr
	})
	return err
}

func (structure *jsonIndexStructure) queryPostings(term string) ([]int, error) {
	return structure.loaded[term], nil
}

func (structure *jsonIndexStructure) addBook(bookID int, tokens []string) error {
	return datamarts.AddBookJSON(bookID, tokens, structure.path())
}

func (structure *jsonIndexStructure) storageUsage() (DiskUsage, error) {
	return MeasureDiskUsage(structure.path())
}

func (structure *jsonIndexStructure) close() error { return nil }

// folderIndexStructure runs the experiments on the per-term folder tree.
type folderIndexStructure struct {
	suite Suite
}

func (structure *folderIndexStructure) name() string { return "folder_index" }

func (structure *folderIndexStructure) path() string {
	return structure.suite.outputPath("datamarts", "inverted_index")
}

func (structure *folderIndexStructure) reset() error {
	return resetDirectory(structure.path())
}

func (structure *folderIndexStructure) build(books []datamarts.TokenizedBook) error {
	return datamarts.SaveFolder(datamarts.BuildPostings(books), structure.path())
}

func (structure *folderIndexStructure) prepareQuery() error { return nil }

func (structure *folderIndexStructure) queryPostings(term string) ([]int, error) {
	return datamarts.QueryFolder(term, structure.path())
}

func (structure *folderIndexStructure) addBook(bookID int, tokens []string) error {
	return datamarts.UpdateFolder(bookID, tokens, structure.path())
}

func (structure *folderIndexStructure) storageUsage() (DiskUsage, error) {
	return MeasureDiskUsage(structure.path())
}

func (structure *folderIndexStructure) close() error { return nil }

// mongoIndexStructure runs the experiments on the MongoDB collection.
type mongoIndexStructure struct {
	suite Suite
	index *datamarts.MongoIndex
	ctx   context.Context
}

func (structure *mongoIndexStructure) name() string { return "mongo_index" }

func (structure *mongoIndexStructure) reset() error {
	return structure.index.Clear(structure.ctx)
}

func (structure *mongoIndexStructure) build(books []datamarts.TokenizedBook) error {
	return structure.index.Save(structure.ctx, datamarts.BuildPostings(books))
}

func (structure *mongoIndexStructure) prepareQuery() error { return nil }

func (structure *mongoIndexStructure) queryPostings(term string) ([]int, error) {
	return structure.index.Query(structure.ctx, term)
}

func (structure *mongoIndexStructure) addBook(bookID int, tokens []string) error {
	return structure.index.UpdateBook(structure.ctx, bookID, tokens)
}

// storageUsage mirrors storage_usage(): storage size of the collection only,
// with zero file and directory counts.
func (structure *mongoIndexStructure) storageUsage() (DiskUsage, error) {
	stats, err := structure.index.StorageStats(structure.ctx)
	if err != nil {
		return DiskUsage{}, err
	}
	path := structure.suite.config.MongoURI + "/" +
		structure.suite.config.MongoDatabase + "." + structure.suite.config.MongoCollection
	return DiskUsage{Path: path, SizeMB: toMB(stats.StorageBytes)}, nil
}

func (structure *mongoIndexStructure) close() error {
	return structure.index.Close(structure.ctx)
}

// runQueryWorkload times every shared query QueryRepetitions times: a query
// matches the documents that contain all of its terms.
func (suite Suite) runQueryWorkload(lookup func(term string) ([]int, error)) ([]time.Duration, error) {
	durations := make([]time.Duration, 0, len(suite.config.Queries)*suite.config.QueryRepetitions)
	for repetition := 0; repetition < suite.config.QueryRepetitions; repetition++ {
		for _, query := range suite.config.Queries {
			start := time.Now()
			if _, err := intersectPostings(query, lookup); err != nil {
				return nil, err
			}
			durations = append(durations, time.Since(start))
		}
	}
	return durations, nil
}
