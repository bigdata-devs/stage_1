package datalake;

import java.nio.file.Path;

public class BatchBased {
    public static boolean download(int bookId) {
        return download(bookId, Downloader.PROJECT_ROOT.resolve("datalake"), 1000);
    }

    public static boolean download(int bookId, Path basePath, int batchSize) {
        int lowerBound = (bookId / batchSize) * batchSize;
        int upperBound = lowerBound + batchSize - 1;
        
        Path outputPath = basePath.resolve("batch_" + lowerBound + "_" + upperBound);
        return Downloader.fetchAndSave(bookId, outputPath);
    }
}