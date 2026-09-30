package datamarts

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"
)

// Connection defaults shared with src/datamarts/inverted_index/mongo_index.py.
const (
	DefaultMongoURI       = "mongodb://localhost:27017"
	DefaultDatabaseName   = "search_engine"
	DefaultCollectionName = "inverted_index"
	connectionTimeout     = 2000 * time.Millisecond
)

// termDocument is the stored shape: {"term": "...", "postings": [...]}.
// Postings are int32, the BSON type pymongo uses for small Python ints.
type termDocument struct {
	Term     string  `bson:"term"`
	Postings []int32 `bson:"postings"`
}

// MongoIndex is the NoSQL structure: one document per term.
type MongoIndex struct {
	client     *mongo.Client
	collection *mongo.Collection
}

// MongoStorageStats summarises the space used by the index collection.
type MongoStorageStats struct {
	Documents    int64
	DataBytes    int64
	StorageBytes int64
	IndexBytes   int64
}

// ConnectMongoIndex mirrors get_collection(): it connects with a 2 s server
// selection timeout and ensures a unique ascending index on "term".
func ConnectMongoIndex(ctx context.Context, uri, databaseName, collectionName string) (*MongoIndex, error) {
	client, err := mongo.Connect(ctx, clientOptions(uri))
	if err != nil {
		return nil, fmt.Errorf("connect to MongoDB: %w", err)
	}
	collection := client.Database(databaseName).Collection(collectionName)
	uniqueTerm := mongo.IndexModel{
		Keys:    bson.D{{Key: "term", Value: 1}},
		Options: options.Index().SetUnique(true),
	}
	if _, err := collection.Indexes().CreateOne(ctx, uniqueTerm); err != nil {
		client.Disconnect(ctx)
		return nil, fmt.Errorf("create term index: %w", err)
	}
	return &MongoIndex{client: client, collection: collection}, nil
}

// IsMongoAvailable mirrors is_available(): a ping with the same timeout.
func IsMongoAvailable(ctx context.Context, uri string) bool {
	client, err := mongo.Connect(ctx, clientOptions(uri))
	if err != nil {
		return false
	}
	defer client.Disconnect(ctx)
	return client.Ping(ctx, readpref.Primary()) == nil
}

func clientOptions(uri string) *options.ClientOptions {
	return options.Client().ApplyURI(uri).SetServerSelectionTimeout(connectionTimeout)
}

// Save mirrors save_index(): wipe the collection, then one insert_many call
// with every term document (the driver splits it into wire-level batches).
func (index *MongoIndex) Save(ctx context.Context, invertedIndex InvertedIndex) error {
	if _, err := index.collection.DeleteMany(ctx, bson.D{}); err != nil {
		return fmt.Errorf("clear collection: %w", err)
	}
	documents := toTermDocuments(invertedIndex)
	if len(documents) == 0 {
		return nil
	}
	if _, err := index.collection.InsertMany(ctx, documents); err != nil {
		return fmt.Errorf("insert term documents: %w", err)
	}
	return nil
}

func toTermDocuments(invertedIndex InvertedIndex) []interface{} {
	documents := make([]interface{}, 0, invertedIndex.TermCount())
	for _, entry := range invertedIndex.Entries() {
		postings := make([]int32, len(entry.Postings))
		for position, bookID := range entry.Postings {
			postings[position] = int32(bookID)
		}
		documents = append(documents, termDocument{Term: entry.Term, Postings: postings})
	}
	return documents
}

// Query mirrors query_index(): a find_one on "term" projecting only the
// postings; an unknown term yields an empty list.
func (index *MongoIndex) Query(ctx context.Context, term string) ([]int, error) {
	projection := options.FindOne().SetProjection(bson.D{{Key: "_id", Value: 0}, {Key: "postings", Value: 1}})
	var document struct {
		Postings []int `bson:"postings"`
	}
	err := index.collection.FindOne(ctx, bson.D{{Key: "term", Value: term}}, projection).Decode(&document)
	if errors.Is(err, mongo.ErrNoDocuments) {
		return []int{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("query term %q: %w", term, err)
	}
	return document.Postings, nil
}

// StorageStats reads collStats, the MongoDB equivalent of a disk-usage scan.
func (index *MongoIndex) StorageStats(ctx context.Context) (MongoStorageStats, error) {
	command := bson.D{{Key: "collStats", Value: index.collection.Name()}}
	var stats bson.M
	if err := index.collection.Database().RunCommand(ctx, command).Decode(&stats); err != nil {
		return MongoStorageStats{}, fmt.Errorf("read collection stats: %w", err)
	}
	return MongoStorageStats{
		Documents:    asInt64(stats["count"]),
		DataBytes:    asInt64(stats["size"]),
		StorageBytes: asInt64(stats["storageSize"]),
		IndexBytes:   asInt64(stats["totalIndexSize"]),
	}, nil
}

// asInt64 normalises the numeric BSON types MongoDB uses in collStats.
func asInt64(value interface{}) int64 {
	switch number := value.(type) {
	case int32:
		return int64(number)
	case int64:
		return number
	case float64:
		return int64(number)
	default:
		return 0
	}
}

// Drop removes the whole database (used by the tests).
func (index *MongoIndex) Drop(ctx context.Context) error {
	return index.collection.Database().Drop(ctx)
}

// Close disconnects the client.
func (index *MongoIndex) Close(ctx context.Context) error {
	return index.client.Disconnect(ctx)
}
