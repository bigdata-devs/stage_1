package benchmark

import (
	"fmt"
	"io/fs"
	"path/filepath"
)

// DiskUsage mirrors the dictionary returned by measure_disk_usage().
type DiskUsage struct {
	Path      string
	SizeMB    float64
	FileCount int
	DirCount  int
}

// MeasureDiskUsage sums the size of every file below path and counts files
// and sub-directories (the root itself is not counted, as with rglob("*")).
// A plain file, such as the monolithic JSON index, counts as one file.
func MeasureDiskUsage(path string) (DiskUsage, error) {
	usage := DiskUsage{Path: path}
	var totalBytes int64
	err := filepath.WalkDir(path, func(current string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() {
			if current != path {
				usage.DirCount++
			}
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		totalBytes += info.Size()
		usage.FileCount++
		return nil
	})
	if err != nil {
		return DiskUsage{}, fmt.Errorf("measure disk usage of %s: %w", path, err)
	}
	usage.SizeMB = toMB(totalBytes)
	return usage, nil
}
