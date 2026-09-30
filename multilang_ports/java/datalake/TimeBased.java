package datalake;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.stream.Stream;

public final class TimeBased implements Layout {

    private static final DateTimeFormatter DATE_PATTERN = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final DateTimeFormatter HOUR_PATTERN = DateTimeFormatter.ofPattern("HH");

    @Override
    public String name() {
        return "time_based";
    }

    @Override
    public Path directory(Path root, int bookId) {
        LocalDateTime now = LocalDateTime.now();
        return root.resolve(now.format(DATE_PATTERN)).resolve(now.format(HOUR_PATTERN));
    }

    @Override
    public LocatedBook locate(Path root, int bookId) throws IOException {
        String bodyName = bookId + Layout.BODY_SUFFIX;
        String headerName = bookId + Layout.HEADER_SUFFIX;
        Path newestBody;
        try (Stream<Path> paths = Files.walk(root)) {
            newestBody = paths.filter(Files::isRegularFile)
                .filter(path -> path.getFileName().toString().equals(bodyName))
                .filter(path -> Files.isRegularFile(path.resolveSibling(headerName)))
                .max(Comparator.naturalOrder())
                .orElse(null);
        }
        if (newestBody == null) {
            throw new NoSuchFileException(bodyName);
        }
        return new LocatedBook(newestBody, newestBody.resolveSibling(headerName));
    }

    public static boolean download(int bookId) {
        return download(bookId, Layout.defaultRoot());
    }

    public static boolean download(int bookId, Path basePath) {
        return new Datalake(basePath, new TimeBased()).download(new GutenbergFetcher(), bookId);
    }
}
