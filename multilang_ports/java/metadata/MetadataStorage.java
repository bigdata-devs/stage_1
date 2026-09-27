package metadata;

import java.util.Map;

public interface MetadataStorage {
    void save(Map<String, Object> metadata);
}