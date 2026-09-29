package benchmark

import (
	"errors"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestMeasureRecordsElapsedTimeAndAllocations(t *testing.T) {
	var sink []byte
	measurement, err := Measure("allocate", func() error {
		sink = make([]byte, 8*bytesPerMB)
		time.Sleep(5 * time.Millisecond)
		return nil
	})
	if err != nil || len(sink) == 0 {
		t.Fatal(err)
	}
	if measurement.Elapsed < 5*time.Millisecond || measurement.TotalAllocMB < 8 {
		t.Fatalf("unexpected measurement %+v", measurement)
	}
}

func TestMeasurePropagatesOperationErrors(t *testing.T) {
	failure := errors.New("boom")
	if _, err := Measure("fail", func() error { return failure }); !errors.Is(err, failure) {
		t.Fatalf("expected the operation error, got %v", err)
	}
}

func TestThroughputValidatesInput(t *testing.T) {
	if value, err := Throughput(10, 2*time.Second); err != nil || value != 5 {
		t.Fatalf("unexpected throughput %v (err %v)", value, err)
	}
	if _, err := Throughput(10, 0); err == nil {
		t.Fatal("expected an error for zero elapsed time")
	}
	if _, err := Throughput(-1, time.Second); err == nil {
		t.Fatal("expected an error for a negative count")
	}
}

func TestCalculateStatisticsUsesSampleStandardDeviation(t *testing.T) {
	stats, err := CalculateStatistics([]time.Duration{time.Second, 2 * time.Second, 3 * time.Second, 4 * time.Second})
	if err != nil {
		t.Fatal(err)
	}
	// statistics.stdev([1, 2, 3, 4]) == 1.2909944487358056
	if stats.MeanSeconds != 2.5 || math.Abs(stats.StdevSeconds-1.2909944487358056) > 1e-12 {
		t.Fatalf("unexpected statistics %+v", stats)
	}
	if stats.MinSeconds != 1 || stats.MaxSeconds != 4 || stats.Iterations != 4 {
		t.Fatalf("unexpected statistics %+v", stats)
	}
}

func TestCalculateStatisticsRejectsEmptyInput(t *testing.T) {
	if _, err := CalculateStatistics(nil); err == nil {
		t.Fatal("expected an error")
	}
}

func TestMeasureDiskUsageCountsFilesAndSubdirectories(t *testing.T) {
	root := t.TempDir()
	os.MkdirAll(filepath.Join(root, "A", "B"), 0o755)
	os.WriteFile(filepath.Join(root, "A", "one.txt"), make([]byte, 1024), 0o644)
	os.WriteFile(filepath.Join(root, "A", "B", "two.txt"), make([]byte, 1024), 0o644)
	usage, err := MeasureDiskUsage(root)
	if err != nil {
		t.Fatal(err)
	}
	if usage.FileCount != 2 || usage.DirCount != 2 || usage.SizeMB != 2048.0/bytesPerMB {
		t.Fatalf("unexpected usage %+v", usage)
	}
}

func TestResultsWriterWritesPythonCompatibleCSV(t *testing.T) {
	writer := ResultsWriter{Dir: t.TempDir()}
	measurement := Measurement{Name: "index_json_build", Elapsed: 1500 * time.Millisecond, MemoryMB: 1.5, CPUPercent: 99.456}
	if err := writer.SaveMeasurement(measurement); err != nil {
		t.Fatal(err)
	}
	if err := writer.SaveMeasurement(measurement); err != nil {
		t.Fatal(err)
	}
	content, _ := os.ReadFile(filepath.Join(writer.Dir, "benchmarks.csv"))
	lines := strings.Split(strings.TrimSuffix(string(content), "\r\n"), "\r\n")
	if len(lines) != 3 || lines[0] != "function_name,elapsed_seconds,memory_mb,cpu_percent,timestamp" {
		t.Fatalf("unexpected CSV:\n%s", content)
	}
	if !strings.HasPrefix(lines[1], "index_json_build,1.500000,1.5000,99.46,") {
		t.Fatalf("unexpected row %q", lines[1])
	}
}
