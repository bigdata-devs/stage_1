package datamarts;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class FolderIndexTest {

    @TempDir
    Path indexDir;

    @Test
    void saveGroupsTermsByUppercaseLetter() throws IOException {
        Map<String, List<Integer>> index = new LinkedHashMap<>();
        index.put("adventure", List.of(5, 12));
        index.put("island", List.of(5));
        index.put("shipwreck", List.of(12));
        FolderIndex.save(index, indexDir);
        String content = Files.readString(indexDir.resolve("A").resolve("adventure.txt"));
        assertEquals("5\n12\n", content);
        assertTrue(Files.isDirectory(indexDir.resolve("I")));
        assertTrue(Files.isDirectory(indexDir.resolve("S")));
    }

    @Test
    void queryReadsTheTermFileAndEmptyForUnknownTerm() throws IOException {
        Map<String, List<Integer>> index = new LinkedHashMap<>();
        index.put("adventure", List.of(5, 12));
        FolderIndex.save(index, indexDir);
        assertEquals(List.of(5, 12), FolderIndex.query("adventure", indexDir));
        assertEquals(List.of(), FolderIndex.query("ghost", indexDir));
        assertEquals(List.of(), FolderIndex.query("", indexDir));
    }

    @Test
    void saveEscapesWindowsReservedNames() throws IOException {
        Map<String, List<Integer>> index = new LinkedHashMap<>();
        for (String term : List.of("con", "aux", "nul", "prn", "console")) {
            index.put(term, List.of(7));
        }
        FolderIndex.save(index, indexDir);
        assertTrue(Files.isRegularFile(indexDir.resolve("C").resolve("con_.txt")));
        assertTrue(Files.isRegularFile(indexDir.resolve("A").resolve("aux_.txt")));
        assertTrue(Files.isRegularFile(indexDir.resolve("N").resolve("nul_.txt")));
        assertTrue(Files.isRegularFile(indexDir.resolve("P").resolve("prn_.txt")));
        assertTrue(Files.isRegularFile(indexDir.resolve("C").resolve("console.txt")));
        assertFalse(Files.exists(indexDir.resolve("C").resolve("con.txt")));
        for (String term : index.keySet()) {
            assertEquals(List.of(7), FolderIndex.query(term, indexDir));
        }
    }

    @Test
    void updateEscapesWindowsReservedNames() throws IOException {
        FolderIndex.update(3, List.of("aux"), indexDir);
        FolderIndex.update(1, List.of("aux"), indexDir);
        assertEquals("1\n3\n", Files.readString(indexDir.resolve("A").resolve("aux_.txt")));
    }

    @Test
    void updateCreatesAndMergesTermFiles() throws IOException {
        FolderIndex.update(12, List.of("island", "ship"), indexDir);
        FolderIndex.update(5, List.of("island"), indexDir);
        assertEquals(List.of(5, 12), FolderIndex.query("island", indexDir));
        assertEquals(List.of(12), FolderIndex.query("ship", indexDir));
    }
}
