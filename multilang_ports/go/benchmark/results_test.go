package benchmark

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestResultsWriterWritesPythonCompatibleScalabilityRow(t *testing.T) {
	writer := ResultsWriter{Dir: t.TempDir()}
	measurement := Measurement{Name: "build_json_index", Elapsed: 1500 * time.Millisecond, MemoryMB: 1.5, CPUPercent: 99.456}
	if err := writer.SaveScalability("build_json_index", 25, measurement); err != nil {
		t.Fatal(err)
	}
	if err := writer.SaveScalability("build_json_index", 50, measurement); err != nil {
		t.Fatal(err)
	}
	content, _ := os.ReadFile(filepath.Join(writer.Dir, "scalability.csv"))
	lines := strings.Split(strings.TrimSuffix(string(content), "\r\n"), "\r\n")
	if len(lines) != 3 || lines[0] != "test_name,batch_size,elapsed_seconds,memory_mb,cpu_percent,timestamp" {
		t.Fatalf("unexpected CSV:\n%s", content)
	}
	if !strings.HasPrefix(lines[1], "build_json_index,25,1.500000,1.5000,99.46,") {
		t.Fatalf("unexpected row %q", lines[1])
	}
}

func TestResultsWriterWritesPythonCompatibleRecoveryRow(t *testing.T) {
	writer := ResultsWriter{Dir: t.TempDir()}
	report := RecoveryReport{
		TotalBooks:      100,
		ProcessedBefore: 50,
		ProcessedAfter:  50,
		Duplicated:      0,
		Lost:            0,
		DetectionTime:   3076 * time.Microsecond,
		ProcessingTime:  49708 * time.Microsecond,
		Elapsed:         52819 * time.Microsecond,
	}
	if err := writer.SaveRecovery("recovery_time_based", report); err != nil {
		t.Fatal(err)
	}
	content, _ := os.ReadFile(filepath.Join(writer.Dir, "recovery.csv"))
	lines := strings.Split(strings.TrimSuffix(string(content), "\r\n"), "\r\n")
	expectedHeader := "test_name,total_books,processed_before_interruption,processed_after_resume,duplicated,lost,detection_time,processing_time,elapsed_seconds,timestamp"
	if len(lines) != 2 || lines[0] != expectedHeader {
		t.Fatalf("unexpected CSV:\n%s", content)
	}
	if !strings.HasPrefix(lines[1], "recovery_time_based,100,50,50,0,0,0.003076,0.049708,0.052819,") {
		t.Fatalf("unexpected row %q", lines[1])
	}
}
