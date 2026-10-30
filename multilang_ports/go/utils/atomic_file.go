package utils

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
)

// WriteAtomically mirrors write_text_atomically(): the content is produced
// into a temporary sibling that starts with a dot and ends in ".tmp" (so the
// datalake and index globs never mistake it for a real book or term file),
// forced to stable storage with fsync and then swapped in with rename, so a
// reader sees either the old file or the complete new one. The handle is
// always closed before the swap, as the Python baseline does.
func WriteAtomically(path string, write func(io.Writer) error) error {
	directory := filepath.Dir(path)
	temporary, err := os.CreateTemp(directory, "."+filepath.Base(path)+".*.tmp")
	if err != nil {
		return fmt.Errorf("create temporary file for %s: %w", path, err)
	}
	temporaryName := temporary.Name()
	if err := produce(temporary, write); err != nil {
		temporary.Close()
		removeLeftover(temporaryName)
		return err
	}
	if err := temporary.Close(); err != nil {
		removeLeftover(temporaryName)
		return fmt.Errorf("close %s: %w", temporaryName, err)
	}
	if err := os.Chmod(temporaryName, 0o644); err != nil {
		removeLeftover(temporaryName)
		return fmt.Errorf("chmod %s: %w", temporaryName, err)
	}
	if err := os.Rename(temporaryName, path); err != nil {
		removeLeftover(temporaryName)
		return fmt.Errorf("replace %s: %w", path, err)
	}
	return nil
}

// WriteTextAtomically writes UTF-8 text with the durability of WriteAtomically.
func WriteTextAtomically(path string, content string) error {
	return WriteAtomically(path, func(destination io.Writer) error {
		_, err := io.WriteString(destination, content)
		return err
	})
}

// produce runs the caller's writer and flushes the file to disk before the swap.
func produce(temporary *os.File, write func(io.Writer) error) error {
	if err := write(temporary); err != nil {
		return fmt.Errorf("write %s: %w", temporary.Name(), err)
	}
	if err := temporary.Sync(); err != nil {
		return fmt.Errorf("sync %s: %w", temporary.Name(), err)
	}
	return nil
}

// removeLeftover deletes the temporary file of a failed write, if it still exists.
func removeLeftover(temporaryName string) {
	_ = os.Remove(temporaryName)
}
