package benchmark

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"search_engine_bench/datalake"
	"search_engine_bench/datamarts"
)

const microsecondsPerSecond = 1e6

// Suite runs the datalake (Section 3.1) and inverted-index (Section 4.2)
// benchmarks sequentially, matching the single-threaded Python baseline.
type Suite struct {
	config  Config
	results ResultsWriter
}

// NewSuite prepares a suite that writes its CSV files to config.ResultsDir.
func NewSuite(config Config) Suite {
	return Suite{config: config, results: ResultsWriter{Dir: config.ResultsDir}}
}

// Run executes every enabled benchmark phase.
func (suite Suite) Run() error {
	if !suite.config.SkipDatalake {
		if err := suite.runDatalakeBenchmark(); err != nil {
			return fmt.Errorf("datalake benchmark: %w", err)
		}
	}
	if !suite.config.SkipIndex {
		if err := suite.runIndexBenchmark(); err != nil {
			return fmt.Errorf("index benchmark: %w", err)
		}
	}
	log.Printf("Results appended to %s", suite.config.ResultsDir)
	return nil
}

// measure runs an operation and records it in benchmarks.csv/memstats.csv.
func (suite Suite) measure(name string, operation func() error) (Measurement, error) {
	measurement, err := Measure(name, operation)
	if err != nil {
		return measurement, fmt.Errorf("%s: %w", name, err)
	}
	log.Printf("[%s] %.4fs | mem %.2f MB | alloc %.2f MB | cpu %.1f%%",
		name, measurement.Elapsed.Seconds(), measurement.MemoryMB, measurement.TotalAllocMB, measurement.CPUPercent)
	if err := suite.results.SaveMeasurement(measurement); err != nil {
		return measurement, err
	}
	return measurement, suite.results.SaveMemStats(measurement)
}

// recordThroughput stores items/second for a measured operation.
func (suite Suite) recordThroughput(measurement Measurement, itemCount int) error {
	itemsPerSecond, err := Throughput(itemCount, measurement.Elapsed)
	if err != nil {
		return err
	}
	log.Printf("[%s] throughput %.4f items/s", measurement.Name, itemsPerSecond)
	return suite.results.SaveThroughput(measurement.Name, itemCount, measurement.Elapsed, itemsPerSecond)
}

// recordDiskUsage stores the size, file and directory count of a path.
func (suite Suite) recordDiskUsage(path string) error {
	usage, err := MeasureDiskUsage(path)
	if err != nil {
		return err
	}
	log.Printf("[disk] %s: %.4f MB, %d files, %d dirs", path, usage.SizeMB, usage.FileCount, usage.DirCount)
	return suite.results.SaveDiskUsage(usage)
}

// recordQueryStatistics stores latency statistics for one query workload.
func (suite Suite) recordQueryStatistics(testName string, durations []time.Duration) error {
	stats, err := CalculateStatistics(durations)
	if err != nil {
		return err
	}
	log.Printf("[%s] %d queries, mean %.3f us, stdev %.3f us", testName, stats.Iterations,
		stats.MeanSeconds*microsecondsPerSecond, stats.StdevSeconds*microsecondsPerSecond)
	return suite.results.SaveStatistics(testName, stats)
}

// resetDirectory removes the output of a previous run so that disk usage
// only reflects the current one.
func resetDirectory(path string) error {
	if err := os.RemoveAll(path); err != nil {
		return fmt.Errorf("clean %s: %w", path, err)
	}
	return nil
}

func (suite Suite) outputPath(parts ...string) string {
	return filepath.Join(append([]string{suite.config.OutputDir}, parts...)...)
}

func (suite Suite) fetcher() datalake.Fetcher {
	if suite.config.RawBooksDir != "" {
		return datalake.DirectoryFetcher{Dir: suite.config.RawBooksDir}
	}
	fetcher := datalake.NewGutenbergFetcher()
	fetcher.BaseURL = suite.config.GutenbergURL
	return fetcher
}

func (suite Suite) connectMongo(ctx context.Context) (*datamarts.MongoIndex, error) {
	return datamarts.ConnectMongoIndex(ctx, suite.config.MongoURI, suite.config.MongoDatabase, suite.config.MongoCollection)
}
