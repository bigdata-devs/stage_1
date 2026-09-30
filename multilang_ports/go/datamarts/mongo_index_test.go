package datamarts

import (
	"context"
	"reflect"
	"testing"
)

// testDatabaseName mirrors TEST_DATABASE_NAME in test_mongo_index.py; the
// whole database is dropped after each test.
const testDatabaseName = "search_engine_test"

// connectTestMongo skips the test when MongoDB is not reachable, like the
// pytest.mark.skipif in the Python suite.
func connectTestMongo(t *testing.T) *MongoIndex {
	t.Helper()
	ctx := context.Background()
	if !IsMongoAvailable(ctx, DefaultMongoURI) {
		t.Skip("MongoDB is not available at " + DefaultMongoURI)
	}
	index, err := ConnectMongoIndex(ctx, DefaultMongoURI, testDatabaseName, DefaultCollectionName)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		index.Drop(ctx)
		index.Close(ctx)
	})
	return index
}

func TestMongoSaveAndQuery(t *testing.T) {
	index := connectTestMongo(t)
	ctx := context.Background()
	if err := index.Save(ctx, sampleIndex()); err != nil {
		t.Fatal(err)
	}
	postings, err := index.Query(ctx, "adventure")
	if err != nil || !reflect.DeepEqual(postings, []int{5, 12}) {
		t.Fatalf("unexpected postings %v (err %v)", postings, err)
	}
}

func TestMongoSaveReplacesPreviousIndex(t *testing.T) {
	index := connectTestMongo(t)
	ctx := context.Background()
	if err := index.Save(ctx, sampleIndex()); err != nil {
		t.Fatal(err)
	}
	replacement := BuildPostings([]TokenizedBook{{ID: 1, Tokens: []string{"castle"}}})
	if err := index.Save(ctx, replacement); err != nil {
		t.Fatal(err)
	}
	postings, err := index.Query(ctx, "adventure")
	if err != nil || len(postings) != 0 {
		t.Fatalf("expected the old term to be gone, got %v (err %v)", postings, err)
	}
	stats, err := index.StorageStats(ctx)
	if err != nil || stats.Documents != 1 {
		t.Fatalf("expected 1 document, got %+v (err %v)", stats, err)
	}
}

func TestMongoQueryUnknownTermReturnsEmpty(t *testing.T) {
	index := connectTestMongo(t)
	postings, err := index.Query(context.Background(), "ghost")
	if err != nil || len(postings) != 0 {
		t.Fatalf("expected no postings, got %v (err %v)", postings, err)
	}
}

func TestMongoUpdateBookAddsPostingsSorted(t *testing.T) {
	index := connectTestMongo(t)
	ctx := context.Background()
	seed := BuildPostings([]TokenizedBook{{ID: 5, Tokens: []string{"adventure", "island"}}})
	if err := index.Save(ctx, seed); err != nil {
		t.Fatal(err)
	}
	if err := index.UpdateBook(ctx, 12, []string{"adventure", "ship"}); err != nil {
		t.Fatal(err)
	}
	if postings, err := index.Query(ctx, "adventure"); err != nil || !reflect.DeepEqual(postings, []int{5, 12}) {
		t.Fatalf("unexpected postings %v (err %v)", postings, err)
	}
	if postings, err := index.Query(ctx, "ship"); err != nil || !reflect.DeepEqual(postings, []int{12}) {
		t.Fatalf("unexpected postings %v (err %v)", postings, err)
	}
	if err := index.UpdateBook(ctx, 12, []string{"adventure"}); err != nil {
		t.Fatal(err)
	}
	if postings, err := index.Query(ctx, "adventure"); err != nil || !reflect.DeepEqual(postings, []int{5, 12}) {
		t.Fatalf("expected no duplicate, got %v (err %v)", postings, err)
	}
}
