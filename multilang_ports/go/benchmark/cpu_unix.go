//go:build unix

package benchmark

import (
	"syscall"
	"time"
)

// processCPUTime returns the user + system CPU time consumed so far.
func processCPUTime() time.Duration {
	var usage syscall.Rusage
	if err := syscall.Getrusage(syscall.RUSAGE_SELF, &usage); err != nil {
		return 0
	}
	return time.Duration(usage.Utime.Nano() + usage.Stime.Nano())
}
