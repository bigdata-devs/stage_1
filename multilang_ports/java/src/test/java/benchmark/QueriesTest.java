package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class QueriesTest {

    @TempDir
    Path dir;

    @Test
    void loadReadsTermsAndSkipsCommentsAndBlankLines() throws IOException {
        Path workload = dir.resolve("queries.txt");
        Files.writeString(workload, "# comment line\n\n  alpha beta \t gamma\nalpha\n");

        List<List<String>> queries = Queries.load(workload);

        assertEquals(List.of(List.of("alpha", "beta", "gamma"), List.of("alpha")), queries);
    }

    @Test
    void loadRejectsAnEmptyWorkload() throws IOException {
        Path workload = dir.resolve("queries.txt");
        Files.writeString(workload, "# nothing here\n\n");

        assertThrows(IOException.class, () -> Queries.load(workload));
    }

    @Test
    void intersectKeepsDocumentsThatContainEveryTerm() throws IOException {
        Map<String, List<Integer>> postings = Map.of(
            "alpha", List.of(1, 2, 3),
            "beta", List.of(2, 3, 4),
            "gamma", List.of(9));

        assertEquals(List.of(2, 3),
            Queries.intersect(List.of("alpha", "beta"), term -> postings.getOrDefault(term, List.of())));
    }

    @Test
    void intersectReturnsEmptyWhenAnyTermIsMissing() throws IOException {
        assertEquals(List.of(),
            Queries.intersect(List.of("alpha", "missing"),
                term -> term.equals("alpha") ? List.of(1, 2) : List.of()));
    }
}
