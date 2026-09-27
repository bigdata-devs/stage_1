package metadata;


import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import org.bson.Document;
import java.util.Map;


public class MongoStorage implements MetadataStorage {
    private MongoClient mongoClient;
    private MongoDatabase database;
    private MongoCollection<Document> collection;


    public MongoStorage(String connectionString, String dbName, String collectionName) {
        this.mongoClient = MongoClients.create(connectionString);
        this.database = this.mongoClient.getDatabase(dbName);
        this.collection = this.database.getCollection(collectionName);
    }


    @Override
    public void save(Map<String, Object> metadata) {
        try {
            Document document = new Document(metadata);
            collection.insertOne(document);
            System.out.println("Document successfully saved to MongoDB..");
        } catch (Exception e) {
            System.err.println("Error saving to MongoDB: " + e.getMessage());
        }
    }

    public void close() {
        if (mongoClient != null) {
            mongoClient.close();
        }
    }
}
