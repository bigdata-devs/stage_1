package datalake;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;

public final class BatchBased implements Layout {

    private static final int DEFAULT_BATCH_SIZE = 1000;

    private final int batchSize;

    public BatchBased() {
        this(DEFAULT_BATCH_SIZE);
    }

    public BatchBased(int batchSize) {
        this.batchSize = batchSize;
    }

    @Override
    public String name() {
        return "batch_based";
    }

    @Override
    public Path directory(Path root, int bookId) {
        int lowerBound = (bookId / batchSize) * batchSize;
        int upperBound = lowerBound + batchSize - 1;
        return root.resolve("batch_" + lowerBound + "_" + upperBound);
    }

    @Override
    public LocatedBook locate(Path root, int bookId) throws IOException {
        Path directory = directory(root, bookId);
        Path body = directory.resolve(bookId + Layout.BODY_SUFFIX);
        Path header = directory.resolve(bookId + Layout.HEADER_SUFFIX);
        if (!Files.isRegularFile(body) || !Files.isRegularFile(header)) {
            throw new NoSuchFileException(body.toString());
        }
        return new LocatedBook(body, header);
    }

    public static boolean download(int bookId) {
        return download(bookId, Layout.defaultRoot(), DEFAULT_BATCH_SIZE);
    }

    public static boolean download(int bookId, Path basePath) {
        return download(bookId, basePath, DEFAULT_BATCH_SIZE);
    }

    public static boolean download(int bookId, Path basePath, int batchSize) {
        return new Datalake(basePath, new BatchBased(batchSize)).download(new GutenbergFetcher(), bookId);
    }
}
