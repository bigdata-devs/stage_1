package datalake;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
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

    /**
     * Probes the exact file names inside every {@code YYYYMMDD/HH} folder, newest first, instead of walking
     * every stored file, like {@code find_time_based_book()}.
     */
    @Override
    public LocatedBook locate(Path root, int bookId) throws IOException {
        return hourDirectoriesNewestFirst(root).stream()
            .map(hourDirectory -> completeCopy(hourDirectory, bookId))
            .flatMap(Optional::stream)
            .findFirst()
            .orElseThrow(() -> new NoSuchFileException(bookId + Layout.BODY_SUFFIX));
    }

    private static List<Path> hourDirectoriesNewestFirst(Path root) throws IOException {
        List<Path> hourDirectories = new ArrayList<>();
        for (Path dateDirectory : subdirectories(root)) {
            hourDirectories.addAll(subdirectories(dateDirectory));
        }
        hourDirectories.sort(Comparator.reverseOrder());
        return hourDirectories;
    }

    private static List<Path> subdirectories(Path directory) throws IOException {
        try (Stream<Path> entries = Files.list(directory)) {
            return entries.filter(Files::isDirectory).toList();
        }
    }

    private static Optional<LocatedBook> completeCopy(Path directory, int bookId) {
        Path body = directory.resolve(bookId + Layout.BODY_SUFFIX);
        Path header = directory.resolve(bookId + Layout.HEADER_SUFFIX);
        if (Files.isRegularFile(body) && Files.isRegularFile(header)) {
            return Optional.of(new LocatedBook(body, header));
        }
        return Optional.empty();
    }

    public static boolean download(int bookId) {
        return download(bookId, Layout.defaultRoot());
    }

    public static boolean download(int bookId, Path basePath) {
        return new Datalake(basePath, new TimeBased()).download(new GutenbergFetcher(), bookId);
    }
}
