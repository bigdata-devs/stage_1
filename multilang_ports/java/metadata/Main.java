package metadata;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        String outputFolder = "data/test_datalake";
        
        try {
            Path dataDir = Paths.get("data");
            if (!Files.exists(dataDir)) {
                Files.createDirectories(dataDir);
                System.out.println("'data' directory created.");
            }
        } catch (IOException e) {
            System.err.println("Error creating the 'data' directory: " + e.getMessage());
            return;
        }

        MetadataStorage currentDb;

        String sqliteDbPath = "data/metadata.db";
        currentDb = new SqliteStorage(sqliteDbPath, "books_metadata");

        //String pgUrl = "jdbc:postgresql://localhost:5432/bigdata_project";
        //String pgUser = "postgres";
        //String pgPassword = " ";
        //currentDb = new PostgresStorage(pgUrl, pgUser, pgPassword, "books_metadata");

        //String mongoConnString = "mongodb://localhost:27017";
        //String mongoDbName = "bigdata_project";
        //currentDb = new MongoStorage(mongoConnString, mongoDbName, "books_metadata");

        System.out.println("Starting processing using: " + currentDb.getClass().getSimpleName());
        
        Map<String, Object> bookMetadata = BookProcessor.processBook(1342, outputFolder, currentDb);

        if (bookMetadata != null) {
            System.out.println("Text files successfully generated.");
            System.out.println("Metadata extracted and saved to the selected database.");
            System.out.println(bookMetadata);
        } else {
            System.err.println("Failed to process the book.");
        }
    }
}