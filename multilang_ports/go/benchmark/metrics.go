// Package benchmark measures the Go port with the same metrics that
// src/utils/benchmarks produces for the Python baseline: wall time, memory,
// CPU usage, throughput, disk usage and query-latency statistics.
package benchmark

import (
	"errors"
	"math"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const bytesPerMB = 1024 * 1024

// Measurement is the result of running one measured operation.
type Measurement struct {
	Name    string
	Elapsed time.Duration
	// MemoryMB is the growth of the resident set size (VmRSS from
	// /proc/self/status), clamped at zero: the same RSS delta that
	// psutil reports in measure_memory() for Python and that rss_bytes()
	// reports for Rust and Java. It is 0 when procfs is unavailable.
	MemoryMB float64
	// HeapAllocDeltaMB is the change in live heap bytes (may be negative).
	HeapAllocDeltaMB float64
	// TotalAllocMB is the volume of heap memory allocated during the run,
	// including memory already reclaimed by the garbage collector.
	TotalAllocMB float64
	// HeapInUseMB is the heap in use when the operation finished.
	HeapInUseMB float64
	// GCCycles is the number of garbage collections during the run.
	GCCycles uint32
	// CPUPercent is process CPU time divided by wall time, like
	// psutil.Process().cpu_percent() (it may exceed 100 on several cores).
	CPUPercent float64
}

// Measure runs operation once and records time, memory and CPU usage.
func Measure(name string, operation func() error) (Measurement, error) {
	memoryBefore := rssBytes()
	var statsBefore, statsAfter runtime.MemStats
	runtime.ReadMemStats(&statsBefore)
	cpuBefore := processCPUTime()
	start := time.Now()

	err := operation()

	elapsed := time.Since(start)
	cpuUsed := processCPUTime() - cpuBefore
	memoryAfter := rssBytes()
	runtime.ReadMemStats(&statsAfter)
	return Measurement{
		Name:             name,
		Elapsed:          elapsed,
		MemoryMB:         math.Max(toMB(int64(memoryAfter)-int64(memoryBefore)), 0),
		HeapAllocDeltaMB: toMB(int64(statsAfter.HeapAlloc) - int64(statsBefore.HeapAlloc)),
		TotalAllocMB:     toMB(int64(statsAfter.TotalAlloc - statsBefore.TotalAlloc)),
		HeapInUseMB:      toMB(int64(statsAfter.HeapInuse)),
		GCCycles:         statsAfter.NumGC - statsBefore.NumGC,
		CPUPercent:       cpuPercent(cpuUsed, elapsed),
	}, err
}

// rssBytes returns the current resident set size of this process in bytes.
// It reads /proc/self/status like the Rust and Java ports do; on systems
// without procfs it reports 0, which also matches their behaviour.
func rssBytes() uint64 {
	data, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return 0
	}
	return residentSetBytes(string(data))
}

func residentSetBytes(status string) uint64 {
	for _, line := range strings.Split(status, "\n") {
		if !strings.HasPrefix(line, "VmRSS:") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 2 {
			return 0
		}
		kilobytes, err := strconv.ParseUint(fields[1], 10, 64)
		if err != nil {
			return 0
		}
		return kilobytes * 1024
	}
	return 0
}

func toMB(bytes int64) float64 {
	return float64(bytes) / bytesPerMB
}

func cpuPercent(cpuUsed time.Duration, elapsed time.Duration) float64 {
	if elapsed <= 0 {
		return 0
	}
	return float64(cpuUsed) / float64(elapsed) * 100
}

// Throughput mirrors calculate_throughput(): items per second.
func Throughput(itemCount int, elapsed time.Duration) (float64, error) {
	if elapsed <= 0 {
		return 0, errors.New("elapsed time must be greater than zero")
	}
	if itemCount < 0 {
		return 0, errors.New("item count cannot be negative")
	}
	return float64(itemCount) / elapsed.Seconds(), nil
}

// Statistics mirrors the dictionary returned by calculate_statistics().
type Statistics struct {
	Iterations   int
	MeanSeconds  float64
	StdevSeconds float64
	MinSeconds   float64
	MaxSeconds   float64
}

// CalculateStatistics uses the sample standard deviation, like Python's
// statistics.stdev(), and reports 0 for a single observation.
func CalculateStatistics(durations []time.Duration) (Statistics, error) {
	if len(durations) == 0 {
		return Statistics{}, errors.New("durations must not be empty")
	}
	stats := Statistics{Iterations: len(durations), MinSeconds: math.Inf(1), MaxSeconds: math.Inf(-1)}
	sum := 0.0
	for _, duration := range durations {
		seconds := duration.Seconds()
		sum += seconds
		stats.MinSeconds = math.Min(stats.MinSeconds, seconds)
		stats.MaxSeconds = math.Max(stats.MaxSeconds, seconds)
	}
	stats.MeanSeconds = sum / float64(len(durations))
	stats.StdevSeconds = sampleStandardDeviation(durations, stats.MeanSeconds)
	return stats, nil
}

func sampleStandardDeviation(durations []time.Duration, mean float64) float64 {
	if len(durations) < 2 {
		return 0
	}
	squaredDeviations := 0.0
	for _, duration := range durations {
		deviation := duration.Seconds() - mean
		squaredDeviations += deviation * deviation
	}
	return math.Sqrt(squaredDeviations / float64(len(durations)-1))
}
