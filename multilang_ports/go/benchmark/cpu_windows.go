//go:build windows

package benchmark

import (
	"syscall"
	"time"
)

// processCPUTime returns the user + kernel CPU time consumed so far.
func processCPUTime() time.Duration {
	var creation, exit, kernel, user syscall.Filetime
	process, err := syscall.GetCurrentProcess()
	if err != nil {
		return 0
	}
	if err := syscall.GetProcessTimes(process, &creation, &exit, &kernel, &user); err != nil {
		return 0
	}
	return filetimeDuration(kernel) + filetimeDuration(user)
}

// filetimeDuration converts a FILETIME interval (100 ns ticks) to a Duration.
func filetimeDuration(filetime syscall.Filetime) time.Duration {
	ticks := int64(filetime.HighDateTime)<<32 | int64(filetime.LowDateTime)
	return time.Duration(ticks * 100)
}
