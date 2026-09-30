package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class DiskUsageTest {

    @TempDir
    Path dir;

    @Test
    void singleFileHasOneFileAndNoDirectories() throws IOException {
        Path file = dir.resolve("index.json");
        Files.writeString(file, "0123456789");

        DiskUsage usage = DiskUsage.measure(file);

        assertEquals(1, usage.fileCount());
        assertEquals(0, usage.dirCount());
        assertEquals(10.0 / (1024 * 1024), usage.sizeMb(), 1e-9);
    }

    @Test
    void directoryTreeCountsFilesAndSubdirectoriesButNotTheRoot() throws IOException {
        Files.createDirectories(dir.resolve("a").resolve("b"));
        Files.writeString(dir.resolve("one.txt"), "abc");
        Files.writeString(dir.resolve("a").resolve("two.txt"), "defg");

        DiskUsage usage = DiskUsage.measure(dir);

        assertEquals(2, usage.fileCount());
        assertEquals(2, usage.dirCount());
        assertEquals(7.0 / (1024 * 1024), usage.sizeMb(), 1e-9);
    }

    @Test
    void missingPathIsRejected() {
        assertThrows(IOException.class, () -> DiskUsage.measure(dir.resolve("absent")));
    }
}
