// Package benchmark measures the Go port with the same metrics that
// src/utils/benchmarks produces for the Python baseline: wall time, memory,
// CPU usage, throughput, disk usage and query-latency statistics.
package benchmark

import (
	"errors"
	"math"
	"runtime"
	"time"
)

const bytesPerMB = 1024 * 1024

// Measurement is the result of running one measured operation.
type Measurement struct {
	Name    string
	Elapsed time.Duration
	// MemoryMB is the growth of memory obtained from the OS (MemStats.Sys),
	// clamped at zero. It is the closest analogue of the RSS delta that
	// psutil reports in measure_memory() for Python.
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
	var memoryBefore, memoryAfter runtime.MemStats
	runtime.ReadMemStats(&memoryBefore)
	cpuBefore := processCPUTime()
	start := time.Now()

	err := operation()

	elapsed := time.Since(start)
	cpuUsed := processCPUTime() - cpuBefore
	runtime.ReadMemStats(&memoryAfter)
	return Measurement{
		Name:             name,
		Elapsed:          elapsed,
		MemoryMB:         math.Max(toMB(int64(memoryAfter.Sys)-int64(memoryBefore.Sys)), 0),
		HeapAllocDeltaMB: toMB(int64(memoryAfter.HeapAlloc) - int64(memoryBefore.HeapAlloc)),
		TotalAllocMB:     toMB(int64(memoryAfter.TotalAlloc - memoryBefore.TotalAlloc)),
		HeapInUseMB:      toMB(int64(memoryAfter.HeapInuse)),
		GCCycles:         memoryAfter.NumGC - memoryBefore.NumGC,
		CPUPercent:       cpuPercent(cpuUsed, elapsed),
	}, err
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
