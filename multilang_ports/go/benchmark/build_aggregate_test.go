package benchmark

import (
	"math"
	"testing"
	"time"
)

func TestAggregateBuildAveragesSamplesAndKeepsTheLargestPeak(t *testing.T) {
	measurements := []Measurement{
		{Elapsed: time.Second, MemoryMB: 2, CPUPercent: 40, PeakRSSMB: 10},
		{Elapsed: 3 * time.Second, MemoryMB: 4, CPUPercent: 60, PeakRSSMB: 30},
	}
	aggregate := aggregateBuild(measurements)
	if aggregate.Repetitions != 2 {
		t.Fatalf("unexpected repetitions %d", aggregate.Repetitions)
	}
	if math.Abs(aggregate.ElapsedSeconds-2) > 1e-9 || math.Abs(aggregate.StdevSeconds-math.Sqrt2) > 1e-9 {
		t.Fatalf("unexpected timing %+v", aggregate)
	}
	if math.Abs(aggregate.MemoryMB-3) > 1e-9 || math.Abs(aggregate.CPUPercent-50) > 1e-9 || aggregate.PeakRSSMB != 30 {
		t.Fatalf("unexpected resources %+v", aggregate)
	}
}

func TestBuildRepetitionsShrinksForLargeBatches(t *testing.T) {
	if buildRepetitions(25) != 5 || buildRepetitions(1000) != 5 ||
		buildRepetitions(5000) != 3 || buildRepetitions(10000) != 2 {
		t.Fatal("unexpected repetition counts")
	}
}
