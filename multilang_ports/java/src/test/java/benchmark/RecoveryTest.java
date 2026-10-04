package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import datalake.BookBased;
import datalake.Datalake;
import datalake.Layout;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class RecoveryTest {

    @TempDir
    Path root;

    private final Layout layout = new BookBased();
    private Datalake lake;
    private final List<Integer> bookIds = List.of(1, 2, 3, 4, 5, 6);

    @BeforeEach
    void storeBooks() throws IOException {
        lake = new Datalake(root, layout);
        for (int bookId : bookIds) {
            store(bookId);
        }
    }

    @Test
    void completeLakeResumesTheSecondHalfWithoutLosses() throws IOException {
        RecoveryReport report = Recovery.resumeAfterInterruption(layout, root, bookIds);

        assertEquals(6, report.totalBooks());
        assertEquals(3, report.processedBefore());
        assertEquals(3, report.processedAfter());
        assertEquals(0, report.duplicated());
        assertEquals(0, report.lost());
        assertTrue(report.elapsed().compareTo(report.detectionTime()) >= 0);
    }

    @Test
    void interruptedLakeResumesStoredBooksAndCountsTheLostOnes() throws IOException {
        Files.delete(root.resolve("5").resolve("5_body.txt"));
        Files.delete(root.resolve("6").resolve("6_body.txt"));

        RecoveryReport report = Recovery.resumeAfterInterruption(layout, root, bookIds);

        assertEquals(1, report.processedAfter());
        assertEquals(2, report.lost());
        assertEquals(0, report.duplicated());
    }

    private void store(int bookId) throws IOException {
        lake.store(bookId, "header " + bookId, "body " + bookId);
    }
}
