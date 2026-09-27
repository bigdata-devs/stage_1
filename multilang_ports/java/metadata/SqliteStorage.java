package metadata;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.Map;

public class SqliteStorage implements MetadataStorage {
    private String url;
    private String tableName;

    public SqliteStorage(String dbFilePath, String tableName) {
        this.url = "jdbc:sqlite:" + dbFilePath;
        this.tableName = tableName;
        createTableIfNotExists();
    }

    private void createTableIfNotExists() {
        String sql = "CREATE TABLE IF NOT EXISTS " + tableName + " (" +
                     "book_id INTEGER PRIMARY KEY, " +
                     "title TEXT, " +
                     "author TEXT, " +
                     "language TEXT, " +
                     "capture_date TEXT);";
        try (Connection conn = DriverManager.getConnection(url);
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.execute();
        } catch (SQLException e) {
            System.err.println("Error creating the table in SQLite: " + e.getMessage());
        }
    }

    @Override
    public void save(Map<String, Object> metadata) {
        String sql = "INSERT OR REPLACE INTO " + tableName + " (book_id, title, author, language, capture_date) VALUES (?, ?, ?, ?, ?)";
        
        try (Connection conn = DriverManager.getConnection(url);
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setObject(1, metadata.get("book_id"));
            pstmt.setString(2, (String) metadata.getOrDefault("Title", "Unknown"));
            pstmt.setString(3, (String) metadata.getOrDefault("Author", "Unknown"));
            pstmt.setString(4, (String) metadata.getOrDefault("Language", "Unknown"));
            pstmt.setString(5, (String) metadata.getOrDefault("Capture Date", "Unknown"));
            
            pstmt.executeUpdate();
            System.out.println("Metadata successfully saved to SQLite.");
        } catch (SQLException e) {
            System.err.println("Error saving to SQLite: " + e.getMessage());
        }
    }
}