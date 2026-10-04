package datalake;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collection;
import java.util.List;
import java.util.TreeSet;

public final class Datalake {

    private final Path root;
    private final Layout layout;

    public Datalake(Path root, Layout layout) {
        this.root = root;
        this.layout = layout;
    }

    public Path store(int bookId, String header, String body) throws IOException {
        Path directory = layout.directory(root, bookId);
        Files.createDirectories(directory);
        Files.writeString(directory.resolve(bookId + Layout.BODY_SUFFIX), body, StandardCharsets.UTF_8);
        Files.writeString(directory.resolve(bookId + Layout.HEADER_SUFFIX), header, StandardCharsets.UTF_8);
        return directory;
    }

    public LocatedBook locate(int bookId) throws IOException {
        return layout.locate(root, bookId);
    }

    public boolean download(Fetcher fetcher, int bookId) {
        try {
            Splitter.Split split = Splitter.split(fetcher.fetch(bookId));
            store(bookId, split.header(), split.body());
            return true;
        } catch (IOException | RuntimeException exception) {
            System.err.println("Book " + bookId + " failed: " + exception.getMessage());
            return false;
        }
    }

    public static List<Integer> listBookIds(Path root) throws IOException {
        if (!Files.isDirectory(root)) {
            return List.of();
        }
        TreeSet<Integer> complete = new TreeSet<>();
        try (var paths = Files.walk(root)) {
            paths.filter(Files::isRegularFile)
                .filter(Datalake::isBodyFile)
                .filter(Datalake::hasNumericBookId)
                .forEach(path -> {
                    int bookId = bookIdOfBody(path);
                    Path header = path.resolveSibling(bookId + Layout.HEADER_SUFFIX);
                    if (Files.isRegularFile(header)) {
                        complete.add(bookId);
                    }
                });
        }
        return List.copyOf(complete);
    }

    public static List<Integer> pendingBookIds(Path root, Collection<Integer> known) throws IOException {
        TreeSet<Integer> pending = new TreeSet<>(listBookIds(root));
        pending.removeAll(known);
        return List.copyOf(pending);
    }

    private static boolean isBodyFile(Path path) {
        return path.getFileName().toString().endsWith(Layout.BODY_SUFFIX);
    }

    private static boolean hasNumericBookId(Path path) {
        String name = path.getFileName().toString();
        String rawId = name.substring(0, name.length() - Layout.BODY_SUFFIX.length());
        return !rawId.isEmpty() && rawId.chars().allMatch(Character::isDigit);
    }

    private static int bookIdOfBody(Path path) {
        String name = path.getFileName().toString();
        return Integer.parseInt(name.substring(0, name.length() - Layout.BODY_SUFFIX.length()));
    }
}
