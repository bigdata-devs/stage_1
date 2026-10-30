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
	// MemoryMB is the growth of the resident set size (VmRSS from
	// /proc/self/status), clamped at zero: the same RSS delta that
	// psutil reports in measure_memory() for Python and that rss_bytes()
	// reports for Rust and Java. It is 0 when procfs is unavailable.
	MemoryMB float64
	// PeakRSSMB is the largest resident set size sampled every 50 ms
	// while the operation ran: the absolute footprint of the process.
	PeakRSSMB float64
	// SysDeltaMB is the growth of runtime.MemStats.Sys, the Go-specific
	// view of memory obtained from the OS (it feeds memstats.csv only).
	SysDeltaMB float64
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
	stopPeakSampler := startPeakRssSampler(memoryBefore)
	var statsBefore, statsAfter runtime.MemStats
	runtime.ReadMemStats(&statsBefore)
	cpuBefore := processCPUTime()
	start := time.Now()

	err := operation()

	elapsed := time.Since(start)
	cpuUsed := processCPUTime() - cpuBefore
	memoryAfter := rssBytes()
	peakRSSBytes := stopPeakSampler(memoryAfter)
	runtime.ReadMemStats(&statsAfter)
	return Measurement{
		Name:             name,
		Elapsed:          elapsed,
		MemoryMB:         math.Max(toMB(int64(memoryAfter)-int64(memoryBefore)), 0),
		PeakRSSMB:        toMB(int64(peakRSSBytes)),
		SysDeltaMB:       toMB(int64(statsAfter.Sys) - int64(statsBefore.Sys)),
		HeapAllocDeltaMB: toMB(int64(statsAfter.HeapAlloc) - int64(statsBefore.HeapAlloc)),
		TotalAllocMB:     toMB(int64(statsAfter.TotalAlloc - statsBefore.TotalAlloc)),
		HeapInUseMB:      toMB(int64(statsAfter.HeapInuse)),
		GCCycles:         statsAfter.NumGC - statsBefore.NumGC,
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
	seconds := make([]float64, len(durations))
	stats := Statistics{Iterations: len(seconds), MinSeconds: math.Inf(1), MaxSeconds: math.Inf(-1)}
	for index, duration := range durations {
		seconds[index] = duration.Seconds()
		stats.MinSeconds = math.Min(stats.MinSeconds, seconds[index])
		stats.MaxSeconds = math.Max(stats.MaxSeconds, seconds[index])
	}
	stats.MeanSeconds = meanSeconds(seconds)
	stats.StdevSeconds = sampleStdevSeconds(seconds, stats.MeanSeconds)
	return stats, nil
}

func meanSeconds(seconds []float64) float64 {
	sum := 0.0
	for _, value := range seconds {
		sum += value
	}
	return sum / float64(len(seconds))
}

func sampleStdevSeconds(seconds []float64, mean float64) float64 {
	if len(seconds) < 2 {
		return 0
	}
	squaredDeviations := 0.0
	for _, value := range seconds {
		deviation := value - mean
		squaredDeviations += deviation * deviation
	}
	return math.Sqrt(squaredDeviations / float64(len(seconds)-1))
}
