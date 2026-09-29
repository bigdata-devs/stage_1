package benchmark

// DefaultBookIDs mirrors SAMPLE_BOOK_IDS in download_sample_data.py.
var DefaultBookIDs = []int{1342, 11, 84, 174}

// DefaultQueryTerms is the shared query workload (Section 4.2 requires the
// same workload in every language). It mixes frequent, rare and missing
// terms; keep it identical to the list used by the other ports.
var DefaultQueryTerms = []string{
	"adventure", "island", "shipwreck", "alice", "rabbit", "elizabeth",
	"darcy", "monster", "creature", "portrait", "dorian", "nonexistentterm",
}

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
	// OutputDir receives the datalakes and the index structures.
	OutputDir string
	// ResultsDir receives the CSV result files.
	ResultsDir string

	MongoURI        string
	MongoDatabase   string
	MongoCollection string

	QueryTerms       []string
	QueryRepetitions int

	SkipDatalake bool
	SkipIndex    bool
	SkipMongo    bool
}
