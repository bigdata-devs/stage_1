package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class EquivalenceTest {

    @TempDir
    Path dir;

    @Test
    void canonicalFileContainsTokenPostingsAndQueryLines() throws IOException {
        writeBody(1, "alpha beta alpha");
        writeBody(2, "beta gamma");
        Path idsFile = dir.resolve("ids.txt");
        Files.writeString(idsFile, "1\n2\n");
        Path queriesFile = dir.resolve("queries.txt");
        Files.writeString(queriesFile, "alpha beta\nbeta delta\n");
        Path outputFile = dir.resolve("out.txt");

        Equivalence.run(dir, idsFile, queriesFile, outputFile);

        List<String> lines = Files.readAllLines(outputFile, StandardCharsets.UTF_8);
        assertEquals("tokens\t1\t" + String.join("\t",
            inverted_index.TextProcessor.processText("alpha beta alpha")), lines.get(0));
        assertEquals("tokens\t2\t" + String.join("\t",
            inverted_index.TextProcessor.processText("beta gamma")), lines.get(1));
        assertEquals(List.of("postings\talpha\t1", "postings\tbeta\t1,2",
            "postings\tgamma\t2", "query\t1\t1", "query\t2"), lines.subList(2, lines.size()));
    }

    private void writeBody(int bookId, String text) throws IOException {
        Files.writeString(dir.resolve(bookId + "_body.txt"), text);
    }
}
