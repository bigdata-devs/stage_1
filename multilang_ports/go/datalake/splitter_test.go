package datalake

import (
	"errors"
	"testing"
)

// Same fixture as tests/test_datalake/test_download.py.
const (
	sampleHeader = "Title: Sample Book\nAuthor: Jane Doe"
	sampleBody   = "It was a bright cold day in April."
	sampleText   = sampleHeader + "\n" + StartMarker + " SAMPLE ***\n" + sampleBody + "\n" + EndMarker + " SAMPLE ***\nLicense footer"
)

func TestSplitSeparatesHeaderAndBodyLikePython(t *testing.T) {
	book, err := Split(sampleText)
	if err != nil {
		t.Fatal(err)
	}
	if book.Header != sampleHeader {
		t.Fatalf("unexpected header %q", book.Header)
	}
	// Python keeps the remainder of the start-marker line in the body.
	if expectedBody := "SAMPLE ***\n" + sampleBody; book.Body != expectedBody {
		t.Fatalf("unexpected body %q", book.Body)
	}
}

func TestSplitFailsWithoutStartMarker(t *testing.T) {
	if _, err := Split("no markers here " + EndMarker); !errors.Is(err, ErrMissingMarkers) {
		t.Fatalf("expected ErrMissingMarkers, got %v", err)
	}
}

func TestSplitFailsWithoutEndMarkerAfterStart(t *testing.T) {
	if _, err := Split(EndMarker + " text " + StartMarker + " body"); !errors.Is(err, ErrMissingMarkers) {
		t.Fatalf("expected ErrMissingMarkers, got %v", err)
	}
}

func TestSplitStripsWhitespaceLikePythonStrip(t *testing.T) {
	book, err := Split("\xef\xbb\xbf\x1c Header \r\n" + StartMarker + "\r\n\u00a0Body\x1f\r\n" + EndMarker)
	if err != nil {
		t.Fatal(err)
	}
	// U+FEFF (BOM) is not whitespace in Python, so it must survive.
	if book.Header != "\xef\xbb\xbf\x1c Header" || book.Body != "Body" {
		t.Fatalf("unexpected split %q / %q", book.Header, book.Body)
	}
}
