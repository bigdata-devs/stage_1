package inverted_index;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CorpusTest {

    @TempDir
    Path bodiesDirectory;

    @Test
    void discoverBookIdsReturnsSortedNumericIds() throws IOException {
        Files.writeString(bodiesDirectory.resolve("1342_body.txt"), "text");
        Files.writeString(bodiesDirectory.resolve("11_body.txt"), "text");
        Files.writeString(bodiesDirectory.resolve("notes_body.txt"), "text");
        assertEquals(List.of(11, 1342), Corpus.discoverBookIds(bodiesDirectory));
    }

    @Test
    void loadTokenizesEveryBodyInOrder() throws IOException {
        Files.writeString(bodiesDirectory.resolve("84_body.txt"), "Frankenstein by Shelley");
        Map<Integer, List<String>> books = Corpus.load(bodiesDirectory);
        assertEquals(List.of(84), List.copyOf(books.keySet()));
        assertTrue(books.get(84).contains("frankenstein"));
        assertTrue(books.get(84).contains("shelley"));
    }
}
