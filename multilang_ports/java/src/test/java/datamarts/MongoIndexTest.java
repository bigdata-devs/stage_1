package datamarts;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

class MongoIndexTest {

    private static final String URI = "mongodb://localhost:27017";
    private static final String DATABASE = "search_engine_test";
    private static final String COLLECTION = "inverted_index";

    @Test
    void saveQueryAndUpdateBookFollowPythonSemantics() {
        Assumptions.assumeTrue(MongoIndex.isAvailable(URI));
        try (MongoIndex index = MongoIndex.connect(URI, DATABASE, COLLECTION)) {
            Map<String, List<Integer>> seed = new LinkedHashMap<>();
            seed.put("adventure", List.of(5));
            seed.put("island", List.of(5));
            index.save(seed);
            assertEquals(List.of(5), index.query("adventure"));

            index.updateBook(12, List.of("adventure", "ship"));
            assertEquals(List.of(5, 12), index.query("adventure"));
            assertEquals(List.of(12), index.query("ship"));

            index.updateBook(12, List.of("adventure"));
            assertEquals(List.of(5, 12), index.query("adventure"));

            index.save(Map.of("castle", List.of(1)));
            assertEquals(List.of(), index.query("adventure"));
            MongoStorageStats stats = index.storageStats();
            assertEquals(1, stats.documents());
            assertTrue(stats.storageBytes() > 0);
            index.clear();
            assertEquals(0, index.storageStats().documents());
        }
    }
}
