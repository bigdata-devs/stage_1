package datalake;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class DatalakeTest {

    private static final String RAW_BOOK = """
        Preamble line.

        *** START OF THE PROJECT GUTENBERG EBOOK Frankenstein ***
        The body text.
        *** END OF THE PROJECT GUTENBERG EBOOK Frankenstein ***
        """;

    @TempDir
    Path root;

    @Test
    void storeWritesBothFilesIntoTheDerivedDirectory() throws IOException {
        Path directory = new Datalake(root, new BookBased()).store(84, "header", "body");
        assertEquals(root.resolve("84"), directory);
        assertEquals("body", Files.readString(directory.resolve("84_body.txt")));
        assertEquals("header", Files.readString(directory.resolve("84_header.txt")));
    }

    @Test
    void batchBasedDirectoryCoversThousandBookBlocks() throws IOException {
        Path directory = new Datalake(root, new BatchBased()).store(1500, "header", "body");
        assertEquals(root.resolve("batch_1000_1999"), directory);
    }

    @Test
    void timeBasedStoreWritesUnderDateAndHourDirectories() throws IOException {
        Path directory = new Datalake(root, new TimeBased()).store(11, "header", "body");
        Path relative = root.relativize(directory);
        assertEquals(2, relative.getNameCount());
        assertTrue(relative.getName(0).toString().matches("\\d{8}"));
        assertTrue(relative.getName(1).toString().matches("\\d{2}"));
    }

    @Test
    void locateReturnsTheNewestTimeBasedCopy() throws IOException {
        Path older = Files.createDirectories(root.resolve("20260930").resolve("14"));
        Path newer = Files.createDirectories(root.resolve("20260930").resolve("15"));
        writeBook(older, 1342, "old", "old");
        writeBook(newer, 1342, "new", "new");
        LocatedBook book = new TimeBased().locate(root, 1342);
        assertEquals(newer.resolve("1342_header.txt"), book.headerPath());
        assertEquals(newer.resolve("1342_body.txt"), book.bodyPath());
    }

    @Test
    void timeBasedLocateSkipsNewerIncompleteCopies() throws IOException {
        Path older = Files.createDirectories(root.resolve("20260930").resolve("14"));
        Path newer = Files.createDirectories(root.resolve("20261001").resolve("09"));
        writeBook(older, 1342, "old", "old");
        writeBook(newer, 1342, "new", "new");
        Files.delete(newer.resolve("1342_header.txt"));
        assertEquals(older.resolve("1342_body.txt"), new TimeBased().locate(root, 1342).bodyPath());
    }

    @Test
    void timeBasedLocateOnlyProbesHourFolders() throws IOException {
        writeBook(Files.createDirectories(root.resolve("1342")), 1342, "h", "b");
        writeBook(Files.createDirectories(root.resolve("20260930").resolve("14").resolve("nested")), 1342, "h", "b");
        assertThrows(NoSuchFileException.class, () -> new TimeBased().locate(root, 1342));
    }

    @Test
    void locateFailsWhenAnyFileIsMissing() throws IOException {
        new Datalake(root, new BookBased()).store(84, "header", "body");
        Files.delete(root.resolve("84").resolve("84_header.txt"));
        assertThrows(NoSuchFileException.class, () -> new BookBased().locate(root, 84));
        assertThrows(NoSuchFileException.class, () -> new TimeBased().locate(root, 84));
    }

    @Test
    void listBookIdsReturnsSortedCompleteBooks() throws IOException {
        new Datalake(root, new BookBased()).store(1342, "h", "b");
        new Datalake(root, new BookBased()).store(1000, "h", "b");
        new Datalake(root, new BookBased()).store(84, "h", "b");
        Files.delete(root.resolve("84").resolve("84_header.txt"));
        assertEquals(List.of(1000, 1342), Datalake.listBookIds(root));
    }

    @Test
    void listBookIdsTreatsAMissingDirectoryAsEmpty() throws IOException {
        assertEquals(List.of(), Datalake.listBookIds(root.resolve("absent")));
    }

    @Test
    void pendingBookIdsExcludesKnownBooks() throws IOException {
        new Datalake(root, new BookBased()).store(1, "h", "b");
        new Datalake(root, new BookBased()).store(2, "h", "b");
        new Datalake(root, new BookBased()).store(3, "h", "b");
        assertEquals(List.of(2), Datalake.pendingBookIds(root, List.of(1, 3)));
    }

    @Test
    void downloadSplitsAndStoresTheFetchedText() {
        Datalake lake = new Datalake(root, new BookBased());
        assertTrue(lake.download(bookId -> RAW_BOOK, 84));
        assertEquals("The body text.", readQuietly(root.resolve("84").resolve("84_body.txt")));
        assertTrue(readQuietly(root.resolve("84").resolve("84_header.txt")).startsWith("Preamble line."));
    }

    @Test
    void downloadFailsGracefullyWithoutMarkers() {
        Datalake lake = new Datalake(root, new BookBased());
        assertFalse(lake.download(bookId -> "no Gutenberg markers here", 84));
    }

    private void writeBook(Path directory, int bookId, String header, String body) throws IOException {
        Files.writeString(directory.resolve(bookId + Layout.HEADER_SUFFIX), header);
        Files.writeString(directory.resolve(bookId + Layout.BODY_SUFFIX), body);
    }

    private String readQuietly(Path path) {
        try {
            return Files.readString(path);
        } catch (IOException exception) {
            throw new AssertionError(exception);
        }
    }
}
