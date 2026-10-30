package benchmark;

import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;

public record DiskUsage(String path, double sizeMb, int fileCount, int dirCount) {

    private static final double BYTES_PER_MB = 1024.0 * 1024.0;

    public static DiskUsage measure(Path path) throws IOException {
        if (!Files.exists(path)) {
            throw new IOException("path does not exist: " + path);
        }
        if (!Files.isDirectory(path)) {
            return new DiskUsage(path.toString(), Files.size(path) / BYTES_PER_MB, 1, 0);
        }
        long[] totalBytes = {0};
        long[] fileCount = {0};
        long[] dirCount = {0};
        Files.walkFileTree(path, new SimpleFileVisitor<>() {
            @Override
            public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
                if (!dir.equals(path)) {
                    dirCount[0]++;
                }
                return FileVisitResult.CONTINUE;
            }

            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                totalBytes[0] += attrs.size();
                fileCount[0]++;
                return FileVisitResult.CONTINUE;
            }
        });
        return new DiskUsage(path.toString(), totalBytes[0] / BYTES_PER_MB, (int) fileCount[0], (int) dirCount[0]);
    }
}
