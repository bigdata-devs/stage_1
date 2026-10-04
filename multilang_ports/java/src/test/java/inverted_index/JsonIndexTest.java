package inverted_index;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class JsonIndexTest {

    @TempDir
    Path tempDir;

    @Test
    void saveAndLoadRoundTripPreservesOrder() throws IOException {
        Map<Integer, List<String>> books = new LinkedHashMap<>();
        books.put(11, List.of("alpha", "beta"));
        books.put(84, List.of("beta"));
        Path outputPath = tempDir.resolve("nested").resolve("inverted_index.json");
        JsonIndex.saveIndex(JsonIndex.buildIndex(books), outputPath);
        Map<String, List<Integer>> loaded = JsonIndex.loadIndex(outputPath);
        assertEquals(List.of("alpha", "beta"), List.copyOf(loaded.keySet()));
        assertEquals(List.of(11), loaded.get("alpha"));
        assertEquals(List.of(11, 84), loaded.get("beta"));
    }

    @Test
    void addBookCreatesAndMergesSortedPostings() throws IOException {
        Path outputPath = tempDir.resolve("inverted_index.json");
        JsonIndex.addBook(9, List.of("island", "zebra"), outputPath);
        JsonIndex.addBook(4, List.of("island", "apple"), outputPath);
        Map<String, List<Integer>> loaded = JsonIndex.loadIndex(outputPath);
        assertEquals(List.of(4), loaded.get("apple"));
        assertEquals(List.of(4, 9), loaded.get("island"));
        assertEquals(List.of(9), loaded.get("zebra"));
    }

    @Test
    void loadFailsForMissingFile() {
        assertThrows(IOException.class, () -> JsonIndex.loadIndex(tempDir.resolve("absent.json")));
    }
}
