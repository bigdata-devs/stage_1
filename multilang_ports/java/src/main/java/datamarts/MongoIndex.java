package datamarts;

import inverted_index.Postings;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.bson.BsonArray;
import org.bson.BsonDocument;
import org.bson.BsonInt32;
import org.bson.BsonString;
import org.bson.Document;
import org.bson.conversions.Bson;
import com.mongodb.ConnectionString;
import com.mongodb.MongoClientSettings;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.BulkWriteOptions;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.IndexOptions;
import com.mongodb.client.model.Indexes;
import com.mongodb.client.model.Projections;
import com.mongodb.client.model.UpdateOneModel;
import com.mongodb.client.model.UpdateOptions;
import com.mongodb.client.model.WriteModel;

public final class MongoIndex implements AutoCloseable {

    private static final Duration SERVER_SELECTION_TIMEOUT = Duration.ofSeconds(2);

    private static final int INSERT_CHUNK_SIZE = 5000;

    private final MongoClient client;
    private final MongoDatabase database;
    private final MongoCollection<Document> collection;
    private final String collectionName;

    private MongoIndex(MongoClient client, MongoDatabase database,
            MongoCollection<Document> collection, String collectionName) {
        this.client = client;
        this.database = database;
        this.collection = collection;
        this.collectionName = collectionName;
    }

    public static boolean isAvailable(String uri) {
        try (MongoClient probe = MongoClients.create(settings(uri))) {
            probe.getDatabase("admin").runCommand(new BsonDocument("ping", new BsonInt32(1)));
            return true;
        } catch (RuntimeException exception) {
            return false;
        }
    }

    public static MongoIndex connect(String uri, String databaseName, String collectionName) {
        MongoClient client = MongoClients.create(settings(uri));
        MongoDatabase database = client.getDatabase(databaseName);
        MongoCollection<Document> collection = database.getCollection(collectionName);
        collection.createIndex(Indexes.ascending("term"), new IndexOptions().unique(true));
        return new MongoIndex(client, database, collection, collectionName);
    }

    private static MongoClientSettings settings(String uri) {
        return MongoClientSettings.builder()
            .applyConnectionString(new ConnectionString(uri))
            .applyToClusterSettings(builder -> builder.serverSelectionTimeout(2, TimeUnit.SECONDS))
            .build();
    }

    public void clear() {
        collection.deleteMany(new BsonDocument());
    }

    public void save(Map<String, List<Integer>> index) {
        clear();
        if (index.isEmpty()) {
            return;
        }
        List<Document> chunk = new ArrayList<>(INSERT_CHUNK_SIZE);
        for (Map.Entry<String, List<Integer>> entry : index.entrySet()) {
            chunk.add(new Document("term", entry.getKey()).append("postings", entry.getValue()));
            if (chunk.size() >= INSERT_CHUNK_SIZE) {
                collection.insertMany(chunk);
                chunk.clear();
            }
        }
        if (!chunk.isEmpty()) {
            collection.insertMany(chunk);
        }
    }

    public List<Integer> query(String term) {
        Document document = collection.find(Filters.eq("term", term))
            .projection(Projections.excludeId())
            .first();
        if (document == null) {
            return List.of();
        }
        return document.getList("postings", Integer.class);
    }

    public void updateBook(int bookId, List<String> tokens) {
        List<WriteModel<Document>> operations = new ArrayList<>();
        for (String term : Postings.uniqueTerms(tokens)) {
            operations.add(new UpdateOneModel<Document>(
                Filters.eq("term", term),
                List.of(bookUpdatePipeline(bookId)),
                new UpdateOptions().upsert(true)));
        }
        if (operations.isEmpty()) {
            return;
        }
        collection.bulkWrite(operations, new BulkWriteOptions().ordered(false));
    }

    static Bson bookUpdatePipeline(int bookId) {
        BsonDocument union = new BsonDocument("$setUnion", new BsonArray(List.of(
            new BsonDocument("$ifNull", new BsonArray(List.of(new BsonString("$postings"), new BsonArray()))),
            new BsonArray(List.of(new BsonInt32(bookId))))));
        BsonDocument sorted = new BsonDocument("$sortArray",
            new BsonDocument("input", union).append("sortBy", new BsonInt32(1)));
        return new BsonDocument("$set", new BsonDocument("postings", sorted));
    }

    public MongoStorageStats storageStats() {
        Document stats = database.runCommand(new BsonDocument("collStats", new BsonString(collectionName)));
        return new MongoStorageStats(
            asLong(stats.get("count")),
            asLong(stats.get("size")),
            asLong(stats.get("storageSize")),
            asLong(stats.get("totalIndexSize")));
    }

    private static long asLong(Object value) {
        return value instanceof Number number ? number.longValue() : 0L;
    }

    @Override
    public void close() {
        client.close();
    }
}
