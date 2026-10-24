package benchmark;

import datalake.Datalake;
import datalake.Layout;
import datalake.LocatedBook;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class Recovery {

    private Recovery() {
    }

    public static RecoveryReport resumeAfterInterruption(Layout layout, Path root, List<Integer> bookIds)
            throws IOException {
        List<Integer> processed = Suite.firstIds(bookIds, bookIds.size() / 2);
        long detectionStart = System.nanoTime();
        List<Integer> pending = Datalake.pendingBookIds(root, processed);
        Duration detectionTime = Duration.ofNanos(System.nanoTime() - detectionStart);

        long processingStart = System.nanoTime();
        List<Integer> resumed = readStoredBooks(layout, root, pending);
        Duration processingTime = Duration.ofNanos(System.nanoTime() - processingStart);

        int duplicated = 0;
        int lost = 0;
        Set<Integer> processedBooks = new HashSet<>(processed);
        Set<Integer> resumedBooks = new HashSet<>(resumed);
        for (int bookId : resumed) {
            if (processedBooks.contains(bookId)) {
                duplicated++;
            }
        }
        for (int bookId : bookIds) {
            if (!processedBooks.contains(bookId) && !resumedBooks.contains(bookId)) {
                lost++;
            }
        }
        return new RecoveryReport(bookIds.size(), processed.size(), resumed.size(), duplicated, lost,
            detectionTime, processingTime, detectionTime.plus(processingTime));
    }

    private static List<Integer> readStoredBooks(Layout layout, Path root, List<Integer> bookIds) throws IOException {
        List<Integer> resumed = new ArrayList<>(bookIds.size());
        for (int bookId : bookIds) {
            LocatedBook book = layout.locate(root, bookId);
            Files.readString(book.bodyPath(), StandardCharsets.UTF_8);
            Files.readString(book.headerPath(), StandardCharsets.UTF_8);
            resumed.add(bookId);
        }
        return resumed;
    }
}
