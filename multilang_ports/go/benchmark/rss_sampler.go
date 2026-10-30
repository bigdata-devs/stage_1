package benchmark

import (
	"os"
	"strconv"
	"strings"
	"sync/atomic"
	"time"
)

const rssSampleInterval = 50 * time.Millisecond

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

// startPeakRssSampler samples the resident set size every rssSampleInterval
// until the returned stop function is called, and reports the largest value
// seen including finalBytes.
func startPeakRssSampler(initialBytes uint64) func(finalBytes uint64) uint64 {
	var peakBytes atomic.Uint64
	peakBytes.Store(initialBytes)
	stopSampling := make(chan struct{})
	samplingDone := make(chan struct{})
	go func() {
		defer close(samplingDone)
		ticker := time.NewTicker(rssSampleInterval)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				storeMax(&peakBytes, rssBytes())
			case <-stopSampling:
				return
			}
		}
	}()
	return func(finalBytes uint64) uint64 {
		close(stopSampling)
		<-samplingDone
		storeMax(&peakBytes, finalBytes)
		return peakBytes.Load()
	}
}

func storeMax(value *atomic.Uint64, sample uint64) {
	for {
		current := value.Load()
		if sample <= current || value.CompareAndSwap(current, sample) {
			return
		}
	}
}
