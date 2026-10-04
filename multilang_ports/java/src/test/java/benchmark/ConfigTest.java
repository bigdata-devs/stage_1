package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ConfigTest {

    @TempDir
    Path dir;

    @Test
    void parseReadsExplicitFlags() throws IOException {
        Path queries = workloadFile();

        Config config = Config.parse(new String[] {
            "-ids", "5, 1,3",
            "-bodies", dir.resolve("bodies").toString(),
            "-headers", dir.resolve("headers").toString(),
            "-queries", queries.toString(),
            "-results", dir.resolve("results").toString(),
            "-query-repetitions", "7",
            "-skip-mongo"
        });

        assertEquals(List.of(5, 1, 3), config.bookIds());
        assertEquals(7, config.queryRepetitions());
        assertTrue(config.skipMongo());
        assertFalse(config.skipDatalake());
        assertEquals(1, config.queries().size());
    }

    @Test
    void parseAcceptsInlineValuesAndBareBooleanFlags() throws IOException {
        Config config = Config.parse(new String[] {
            "-ids=8",
            "-queries=" + workloadFile(),
            "-query-repetitions=3",
            "-skip-index"
        });

        assertEquals(List.of(8), config.bookIds());
        assertEquals(3, config.queryRepetitions());
        assertTrue(config.skipIndex());
        assertFalse(config.skipMongo());
    }

    @Test
    void missingIdsFlagDiscoversTheCorpusBodies() throws IOException {
        Path bodies = dir.resolve("bodies");
        Files.createDirectories(bodies);
        Files.writeString(bodies.resolve("84_body.txt"), "text");
        Files.writeString(bodies.resolve("11_body.txt"), "text");

        Config config = Config.parse(new String[] {
            "-bodies", bodies.toString(),
            "-queries", workloadFile().toString()
        });

        assertEquals(List.of(11, 84), config.bookIds());
    }

    @Test
    void zeroRepetitionsAndMissingFlagValuesAreRejected() throws IOException {
        Path queries = workloadFile();

        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {
            "-queries", queries.toString(),
            "-query-repetitions", "0"
        }));
        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {"-bodies"}));
    }

    private Path workloadFile() throws IOException {
        Path queries = dir.resolve("queries.txt");
        Files.writeString(queries, "alpha beta\n");
        return queries;
    }
}
