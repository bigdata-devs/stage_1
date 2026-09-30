// Command search_engine_bench is the Go port of the Stage 1 data layer.
//
// Usage:
//
//	go run . build <bodies_dir> <output_json>   # same contract as the Rust/Java ports
//	go run . query <index_json> <term>...       # same contract as the Rust/Java ports
//	go run . bench [flags]                      # full datalake + inverted index benchmark
//
// Run `go run . bench -h` to list the benchmark flags.
package main

import (
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"search_engine_bench/benchmark"
	"search_engine_bench/datalake"
	"search_engine_bench/datamarts"
	"search_engine_bench/utils"
)

const usage = `Usage: search_engine_bench build <bodies_dir> <output_json>
       search_engine_bench query <index_json> <term>...
       search_engine_bench bench [flags]`

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(args []string) error {
	switch {
	case len(args) == 3 && args[0] == "build":
		return buildJSONIndex(args[1], args[2])
	case len(args) >= 3 && args[0] == "query":
		return queryJSONIndex(args[1], args[2:])
	case len(args) >= 1 && args[0] == "bench":
		return runBenchmark(args[1:])
	default:
		return errors.New(usage)
	}
}

// buildJSONIndex mirrors `index_rust build` / `java Main build`.
func buildJSONIndex(bodiesDir string, outputPath string) error {
	books, err := datamarts.LoadTokenizedBooks(bodiesDir)
	if err != nil {
		return err
	}
	index := datamarts.BuildPostings(books)
	if err := datamarts.SaveJSON(index, outputPath); err != nil {
		return err
	}
	fmt.Printf("Index contains %d unique terms\n", index.TermCount())
	return nil
}

// queryJSONIndex mirrors `index_rust query` / `java Main query`.
func queryJSONIndex(indexPath string, terms []string) error {
	index, err := datamarts.LoadJSON(indexPath)
	if err != nil {
		return err
	}
	for _, term := range terms {
		fmt.Printf("%s: %s\n", term, datamarts.FormatPostings(index[term]))
	}
	return nil
}

func runBenchmark(args []string) error {
	config, err := parseBenchmarkFlags(args)
	if err != nil {
		return err
	}
	log.SetFlags(log.Ldate | log.Ltime)
	return benchmark.NewSuite(config).Run()
}

func parseBenchmarkFlags(args []string) (benchmark.Config, error) {
	flags := flag.NewFlagSet("bench", flag.ContinueOnError)
	config := benchmark.Config{}
	bookIDs := flags.String("ids", "", "comma-separated Gutenberg book IDs for the datalake (default: discovered from -bodies)")
	queriesFile := flags.String("queries", benchmark.DefaultQueriesPath, "path to the shared query workload file")
	flags.StringVar(&config.RawBooksDir, "raw-dir", "", "read raw pg<id>.txt files from this folder instead of downloading")
	flags.StringVar(&config.GutenbergURL, "gutenberg-url", datalake.GutenbergBaseURL, "base URL of the Gutenberg mirror")
	flags.StringVar(&config.BodiesDir, "bodies", benchmark.DefaultBodiesDir, "folder with <id>_body.txt files to index")
	flags.StringVar(&config.HeadersDir, "headers", benchmark.DefaultHeadersDir, "folder with <id>_header.txt files stored in the datalake")
	flags.StringVar(&config.OutputDir, "out", defaultArtifactDir(), "folder for the generated datalakes and indexes")
	flags.StringVar(&config.ResultsDir, "results", "results", "folder for the CSV benchmark results")
	flags.StringVar(&config.MongoURI, "mongo-uri", datamarts.DefaultMongoURI, "MongoDB connection URI")
	flags.StringVar(&config.MongoDatabase, "mongo-db", datamarts.DefaultDatabaseName, "MongoDB database")
	flags.StringVar(&config.MongoCollection, "mongo-collection", datamarts.DefaultCollectionName, "MongoDB collection")
	flags.IntVar(&config.QueryRepetitions, "query-repetitions", 5, "times the shared query workload is repeated")
	flags.BoolVar(&config.SkipDatalake, "skip-datalake", false, "skip the datalake benchmark")
	flags.BoolVar(&config.SkipIndex, "skip-index", false, "skip the inverted index benchmark")
	flags.BoolVar(&config.SkipMongo, "skip-mongo", false, "skip the MongoDB index")
	if err := flags.Parse(args); err != nil {
		return config, err
	}
	if config.QueryRepetitions < 1 {
		return config, errors.New("-query-repetitions must be at least 1")
	}
	queries, err := benchmark.LoadSharedQueries(*queriesFile)
	if err != nil {
		return config, err
	}
	config.Queries = queries
	config.BookIDs, err = bookIDsFrom(*bookIDs, config.BodiesDir)
	return config, err
}

func defaultArtifactDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return "output"
	}
	return filepath.Join(home, ".cache", "stage_1_benchmarks", "go")
}

func bookIDsFrom(flagValue string, bodiesDir string) ([]int, error) {
	if flagValue == "" {
		return utils.DiscoverBookIDs(bodiesDir)
	}
	return parseInts(flagValue)
}

func splitList(commaSeparated string) []string {
	items := []string{}
	for _, item := range strings.Split(commaSeparated, ",") {
		if trimmed := strings.TrimSpace(item); trimmed != "" {
			items = append(items, trimmed)
		}
	}
	return items
}

func parseInts(commaSeparated string) ([]int, error) {
	values := []int{}
	for _, item := range splitList(commaSeparated) {
		value, err := strconv.Atoi(item)
		if err != nil {
			return nil, fmt.Errorf("invalid book id %q: %w", item, err)
		}
		values = append(values, value)
	}
	return values, nil
}
