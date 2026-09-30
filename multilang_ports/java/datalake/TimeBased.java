package datalake;

import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class TimeBased {
    public static boolean download(int bookId) {
        return download(bookId, Downloader.PROJECT_ROOT.resolve("datalake"));
    }

    public static boolean download(int bookId, Path basePath) {
        LocalDateTime now = LocalDateTime.now();
        String dateStr = now.format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        String hourStr = now.format(DateTimeFormatter.ofPattern("HH"));
        
        Path outputPath = basePath.resolve(dateStr).resolve(hourStr);
        return Downloader.fetchAndSave(bookId, outputPath);
    }
}   