// Package datalake ports src/datalake/datalake_engine.py: it downloads (or
// reads) raw Project Gutenberg books, splits them into header and body using
// the official markers and stores both parts in one of three directory
// hierarchies (time-based, book-based and batch/range-based).
package datalake

import (
	"errors"
	"strings"
	"unicode"
)

// StartMarker and EndMarker are the Project Gutenberg delimiters, identical
// to START_MARKER and END_MARKER in the Python baseline.
const (
	StartMarker = "*** START OF THE PROJECT GUTENBERG EBOOK"
	EndMarker   = "*** END OF THE PROJECT GUTENBERG EBOOK"
)

// ErrMissingMarkers is returned when a text lacks the Gutenberg markers.
var ErrMissingMarkers = errors.New("book does not contain the Project Gutenberg start/end markers")

// SplitBook is a raw book divided into its licence header and its body.
type SplitBook struct {
	Header string
	Body   string
}

// Split mirrors the Python logic:
//
//	header, body_and_footer = text.split(START_MARKER, 1)
//	body, footer = body_and_footer.split(END_MARKER, 1)
//	return header.strip(), body.strip()
//
// The markers themselves are dropped, but the rest of the start-marker line
// (e.g. " PRIDE AND PREJUDICE ***") stays in the body, exactly as in Python.
func Split(text string) (SplitBook, error) {
	startIndex := strings.Index(text, StartMarker)
	if startIndex < 0 {
		return SplitBook{}, ErrMissingMarkers
	}
	bodyAndFooter := text[startIndex+len(StartMarker):]
	endIndex := strings.Index(bodyAndFooter, EndMarker)
	if endIndex < 0 {
		return SplitBook{}, ErrMissingMarkers
	}
	return SplitBook{
		Header: stripPythonWhitespace(text[:startIndex]),
		Body:   stripPythonWhitespace(bodyAndFooter[:endIndex]),
	}, nil
}

// stripPythonWhitespace behaves like Python's str.strip(): it trims every
// character for which str.isspace() is true. Go's unicode.IsSpace misses the
// ASCII separators U+001C..U+001F, so they are added explicitly.
func stripPythonWhitespace(text string) string {
	return strings.TrimFunc(text, isPythonWhitespace)
}

func isPythonWhitespace(character rune) bool {
	return unicode.IsSpace(character) || (character >= 0x1C && character <= 0x1F)
}
