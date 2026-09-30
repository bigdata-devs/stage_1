package datalake;

import java.nio.file.Path;

public class BookBased {
    public static boolean download(int bookId) {
        return download(bookId, Downloader.PROJECT_ROOT.resolve("datalake"));
    }

    public static boolean download(int bookId, Path basePath) {
        Path outputPath = basePath.resolve(String.valueOf(bookId));
        return Downloader.fetchAndSave(bookId, outputPath);
    }
}