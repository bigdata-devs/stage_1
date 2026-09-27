package metadata;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.Map;

public class PostgresStorage implements MetadataStorage {
    private String url;
    private String user;
    private String password;
    private String tableName;

    public PostgresStorage(String url, String user, String password, String tableName) {
        this.url = url;
        this.user = user;
        this.password = password;
        this.tableName = tableName;
    }

    @Override
    public void save(Map<String, Object> metadata) {
        String sql = "INSERT INTO " + tableName + " (metadata_key, metadata_value) VALUES (?, ?)";
        try (Connection conn = DriverManager.getConnection(url, user, password);
             PreparedStatement pstmt = conn.prepareStatement(sql)) {

            for (Map.Entry<String, Object> entry : metadata.entrySet()) {
                pstmt.setString(1, entry.getKey());
                pstmt.setString(2, entry.getValue() != null ? entry.getValue().toString() : "");
                pstmt.executeUpdate();
            }
            
            System.out.println("Metadata successfully saved to PostgreSQL.");
        } catch (SQLException e) {
            System.err.println("Error saving to PostgreSQL: " + e.getMessage());
        }
    }
}