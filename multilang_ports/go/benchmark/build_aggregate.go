package benchmark

// BuildAggregate summarises the repeated measurements of one scalability
// batch, mirroring the fields that save_scalability() stores in Python.
type BuildAggregate struct {
	ElapsedSeconds float64
	StdevSeconds   float64
	Repetitions    int
	MemoryMB       float64
	CPUPercent     float64
	PeakRSSMB      float64
}

// aggregateBuild reduces the samples of one batch to their mean behaviour:
// elapsed, memory and CPU are averaged, the peak RSS is the largest sample.
func aggregateBuild(measurements []Measurement) BuildAggregate {
	elapsedSeconds := make([]float64, len(measurements))
	var memoryMB, cpuPercent, peakRSSMB float64
	for index, measurement := range measurements {
		elapsedSeconds[index] = measurement.Elapsed.Seconds()
		memoryMB += measurement.MemoryMB
		cpuPercent += measurement.CPUPercent
		peakRSSMB = max(peakRSSMB, measurement.PeakRSSMB)
	}
	count := float64(len(measurements))
	mean := meanSeconds(elapsedSeconds)
	return BuildAggregate{
		ElapsedSeconds: mean,
		StdevSeconds:   sampleStdevSeconds(elapsedSeconds, mean),
		Repetitions:    len(measurements),
		MemoryMB:       memoryMB / count,
		CPUPercent:     cpuPercent / count,
		PeakRSSMB:      peakRSSMB,
	}
}
