package ingestion;

import java.nio.file.Path;

public class BatchBased {
    public static boolean download(int bookId) {
        return download(bookId, Downloader.PROJECT_ROOT.resolve("datalake"), 1000);
    }

    public static boolean download(int bookId, Path basePath, int batchSize) {
        int rangoInferior = (bookId / batchSize) * batchSize;
        int rangoSuperior = rangoInferior + batchSize - 1;
        
        Path outputPath = basePath.resolve("batch_" + rangoInferior + "_" + rangoSuperior);
        return Downloader.fetchAndSave(bookId, outputPath);
    }
}