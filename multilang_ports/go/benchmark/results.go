package benchmark

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

// pythonISOFormat matches datetime.now().isoformat().
const pythonISOFormat = "2006-01-02T15:04:05.000000"

// ResultsWriter appends CSV rows with the same file names, columns, number
// formats and CRLF line endings as src/utils/benchmarks/storage.py, so Go
// results can be concatenated with the Python ones. memstats.csv is the only
// Go-specific file (it details runtime.MemStats).
type ResultsWriter struct {
	Dir string
}

// SaveMeasurement mirrors save_result() -> benchmarks.csv.
func (writer ResultsWriter) SaveMeasurement(measurement Measurement) error {
	return writer.appendTimestampedRow("benchmarks.csv",
		[]string{"function_name", "elapsed_seconds", "memory_mb", "cpu_percent"},
		[]string{
			measurement.Name,
			formatFloat(measurement.Elapsed.Seconds(), 6),
			formatFloat(measurement.MemoryMB, 4),
			formatFloat(measurement.CPUPercent, 2),
		})
}

// SaveMemStats writes the Go runtime memory details -> memstats.csv.
func (writer ResultsWriter) SaveMemStats(measurement Measurement) error {
	return writer.appendTimestampedRow("memstats.csv",
		[]string{"function_name", "sys_delta_mb", "heap_alloc_delta_mb", "total_alloc_mb", "heap_inuse_mb", "gc_cycles"},
		[]string{
			measurement.Name,
			formatFloat(measurement.MemoryMB, 4),
			formatFloat(measurement.HeapAllocDeltaMB, 4),
			formatFloat(measurement.TotalAllocMB, 4),
			formatFloat(measurement.HeapInUseMB, 4),
			strconv.FormatUint(uint64(measurement.GCCycles), 10),
		})
}

// SaveDiskUsage mirrors save_disk_usage() -> disk_usage.csv.
func (writer ResultsWriter) SaveDiskUsage(usage DiskUsage) error {
	return writer.appendTimestampedRow("disk_usage.csv",
		[]string{"path", "size_mb", "file_count", "dir_count"},
		[]string{usage.Path, formatFloat(usage.SizeMB, 4), strconv.Itoa(usage.FileCount), strconv.Itoa(usage.DirCount)})
}

// SaveThroughput mirrors save_throughput() -> throughput.csv.
func (writer ResultsWriter) SaveThroughput(testName string, itemCount int, elapsed time.Duration, itemsPerSecond float64) error {
	return writer.appendTimestampedRow("throughput.csv",
		[]string{"test_name", "item_count", "elapsed_seconds", "items_per_second"},
		[]string{testName, strconv.Itoa(itemCount), formatFloat(elapsed.Seconds(), 6), formatFloat(itemsPerSecond, 4)})
}

// SaveStatistics mirrors save_statistics() -> statistics.csv.
func (writer ResultsWriter) SaveStatistics(testName string, stats Statistics) error {
	return writer.appendTimestampedRow("statistics.csv",
		[]string{"test_name", "iterations", "mean_seconds", "stdev_seconds", "min_seconds", "max_seconds"},
		[]string{
			testName,
			strconv.Itoa(stats.Iterations),
			formatFloat(stats.MeanSeconds, 6),
			formatFloat(stats.StdevSeconds, 6),
			formatFloat(stats.MinSeconds, 6),
			formatFloat(stats.MaxSeconds, 6),
		})
}

func (writer ResultsWriter) appendTimestampedRow(fileName string, header []string, row []string) error {
	if err := os.MkdirAll(writer.Dir, 0o755); err != nil {
		return fmt.Errorf("create results directory: %w", err)
	}
	filePath := filepath.Join(writer.Dir, fileName)
	_, statErr := os.Stat(filePath)
	isNewFile := errors.Is(statErr, fs.ErrNotExist)
	file, err := os.OpenFile(filePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return fmt.Errorf("open %s: %w", filePath, err)
	}
	defer file.Close()
	csvWriter := csv.NewWriter(file)
	csvWriter.UseCRLF = true
	if isNewFile {
		csvWriter.Write(append(header, "timestamp"))
	}
	csvWriter.Write(append(row, time.Now().Format(pythonISOFormat)))
	csvWriter.Flush()
	return csvWriter.Error()
}

func formatFloat(value float64, decimals int) string {
	return strconv.FormatFloat(value, 'f', decimals, 64)
}
