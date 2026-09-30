package benchmark

// DefaultBodiesDir is the tracked experiment corpus with 100 Gutenberg books.
const DefaultBodiesDir = "../../data_source/bodies"

// DefaultHeadersDir holds the header files of the same tracked corpus.
const DefaultHeadersDir = "../../data_source/headers"

// DefaultQueriesPath is the shared query workload of Section 4.2: every
// language benchmark reads this file and applies the same semantics.
const DefaultQueriesPath = "../../src/utils/benchmarks/queries.txt"

// Config describes one benchmark run.
type Config struct {
	// BookIDs are the Gutenberg books ingested into the datalake.
	BookIDs []int
	// RawBooksDir, when set, reads raw "pg<id>.txt" files instead of
	// downloading them (offline, reproducible datalake runs).
	RawBooksDir string
	// GutenbergURL is the base URL used when downloading.
	GutenbergURL string
	// BodiesDir contains the "<id>_body.txt" files that feed the index.
	BodiesDir string
	// HeadersDir contains the "<id>_header.txt" files stored in the datalake.
	HeadersDir string
	// OutputDir receives the datalakes and the index structures.
	OutputDir string
	// ResultsDir receives the CSV result files.
	ResultsDir string

	MongoURI        string
	MongoDatabase   string
	MongoCollection string

	Queries          [][]string
	QueryRepetitions int

	SkipDatalake bool
	SkipIndex    bool
	SkipMongo    bool
}
