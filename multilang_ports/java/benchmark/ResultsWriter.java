package benchmark;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public final class ResultsWriter {

    private static final DateTimeFormatter TIMESTAMP =
        DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS");

    private final Path dir;

    public ResultsWriter(Path dir) {
        this.dir = dir;
    }

    public void saveMeasurement(Measurement measurement) throws IOException {
        appendTimestampedRow("benchmarks.csv",
            List.of("function_name", "elapsed_seconds", "memory_mb", "cpu_percent"),
            List.of(measurement.name(), format(measurement.seconds(), 6),
                format(measurement.memoryMb(), 4), format(measurement.cpuPercent(), 2)));
    }

    public void saveDiskUsage(DiskUsage usage) throws IOException {
        appendTimestampedRow("disk_usage.csv",
            List.of("path", "size_mb", "file_count", "dir_count"),
            List.of(usage.path(), format(usage.sizeMb(), 4),
                Integer.toString(usage.fileCount()), Integer.toString(usage.dirCount())));
    }

    public void saveThroughput(String testName, int itemCount, Duration elapsed, double itemsPerSecond)
            throws IOException {
        appendTimestampedRow("throughput.csv",
            List.of("test_name", "item_count", "elapsed_seconds", "items_per_second"),
            List.of(testName, Integer.toString(itemCount), format(elapsed.toNanos() / 1e9, 6),
                format(itemsPerSecond, 4)));
    }

    public void saveStatistics(String testName, Statistics statistics) throws IOException {
        appendTimestampedRow("statistics.csv",
            List.of("test_name", "iterations", "mean_seconds", "stdev_seconds", "min_seconds", "max_seconds"),
            List.of(testName, Integer.toString(statistics.iterations()),
                format(statistics.meanSeconds(), 6), format(statistics.stdevSeconds(), 6),
                format(statistics.minSeconds(), 6), format(statistics.maxSeconds(), 6)));
    }

    public void saveScalability(String testName, int batchSize, Measurement measurement) throws IOException {
        appendTimestampedRow("scalability.csv",
            List.of("test_name", "batch_size", "elapsed_seconds", "memory_mb", "cpu_percent"),
            List.of(testName, Integer.toString(batchSize), format(measurement.seconds(), 6),
                format(measurement.memoryMb(), 4), format(measurement.cpuPercent(), 2)));
    }

    public void saveRecovery(String testName, RecoveryReport report) throws IOException {
        appendTimestampedRow("recovery.csv",
            List.of("test_name", "total_books", "processed_before_interruption", "processed_after_resume",
                "duplicated", "lost", "detection_time", "processing_time", "elapsed_seconds"),
            List.of(testName, Integer.toString(report.totalBooks()), Integer.toString(report.processedBefore()),
                Integer.toString(report.processedAfter()), Integer.toString(report.duplicated()),
                Integer.toString(report.lost()), format(report.detectionTime().toNanos() / 1e9, 6),
                format(report.processingTime().toNanos() / 1e9, 6), format(report.elapsed().toNanos() / 1e9, 6)));
    }

    private void appendTimestampedRow(String fileName, List<String> header, List<String> row) throws IOException {
        Files.createDirectories(dir);
        Path filePath = dir.resolve(fileName);
        StringBuilder lines = new StringBuilder();
        if (Files.notExists(filePath)) {
            appendLine(lines, header, true);
        }
        appendLine(lines, row, false);
        Files.writeString(filePath, lines, StandardCharsets.UTF_8,
            StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    private void appendLine(StringBuilder lines, List<String> values, boolean isHeader) {
        List<String> columns = new ArrayList<>(values);
        columns.add(isHeader ? "timestamp" : LocalDateTime.now().format(TIMESTAMP));
        for (int position = 0; position < columns.size(); position++) {
            if (position > 0) {
                lines.append(',');
            }
            lines.append(escape(columns.get(position)));
        }
        lines.append("\r\n");
    }

    private static String escape(String value) {
        if (value.contains(",") || value.contains("\"") || value.contains("\r") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    static String format(double value, int decimals) {
        return String.format(java.util.Locale.ROOT, "%." + decimals + "f", value);
    }
}
