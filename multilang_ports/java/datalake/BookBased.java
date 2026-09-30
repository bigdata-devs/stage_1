package datalake;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;

public final class BookBased implements Layout {

    @Override
    public String name() {
        return "book_based";
    }

    @Override
    public Path directory(Path root, int bookId) {
        return root.resolve(String.valueOf(bookId));
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
        return download(bookId, Layout.defaultRoot());
    }

    public static boolean download(int bookId, Path basePath) {
        return new Datalake(basePath, new BookBased()).download(new GutenbergFetcher(), bookId);
    }
}
