package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ResultsWriterTest {

    @TempDir
    Path dir;

    @Test
    void measurementRowUsesSixFourTwoDecimalsAndCrlf() throws IOException {
        ResultsWriter results = new ResultsWriter(dir);
        results.saveMeasurement(new Measurement("tokenize_books", Duration.ofSeconds(2), 12.5, 33.333));

        String content = Files.readString(dir.resolve("benchmarks.csv"), StandardCharsets.UTF_8);
        List<String> lines = Files.readAllLines(dir.resolve("benchmarks.csv"), StandardCharsets.UTF_8);
        assertEquals("function_name,elapsed_seconds,memory_mb,cpu_percent,timestamp", lines.get(0));
        assertTrue(lines.get(1).matches(
            "tokenize_books,2\\.000000,12\\.5000,33\\.33,\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{6}"));
        assertTrue(content.contains("\r\n"));
    }

    @Test
    void secondRowAppendsWithoutHeader() throws IOException {
        ResultsWriter results = new ResultsWriter(dir);
        results.saveMeasurement(new Measurement("first", Duration.ofSeconds(1), 1.0, 1.0));
        results.saveMeasurement(new Measurement("second", Duration.ofSeconds(3), 2.0, 2.0));

        List<String> lines = Files.readAllLines(dir.resolve("benchmarks.csv"), StandardCharsets.UTF_8);
        assertEquals(3, lines.size());
        assertFalse(lines.get(1).contains("function_name"));
        assertTrue(lines.get(2).startsWith("second,3.000000,2.0000,2.00"));
    }

    @Test
    void statisticsRowUsesSixDecimalsForEveryValue() throws IOException {
        ResultsWriter results = new ResultsWriter(dir);
        results.saveStatistics("query_json_index",
            new Statistics(5, 0.001234, 0.000567, 0.000891, 0.002345));

        String content = Files.readString(dir.resolve("statistics.csv"), StandardCharsets.UTF_8);
        assertTrue(content.contains(
            "query_json_index,5,0.001234,0.000567,0.000891,0.002345,"));
    }

    @Test
    void diskUsageRowStoresFileAndDirectoryCounts() throws IOException {
        ResultsWriter results = new ResultsWriter(dir);
        results.saveDiskUsage(new DiskUsage("/tmp/idx", 4.125, 12, 3));

        List<String> lines = Files.readAllLines(dir.resolve("disk_usage.csv"), StandardCharsets.UTF_8);
        assertEquals(2, lines.size());
        assertEquals("path,size_mb,file_count,dir_count,timestamp", lines.get(0));
        assertTrue(lines.get(1).startsWith("/tmp/idx,4.1250,12,3,"));
    }

    @Test
    void recoveryAndThroughputAndScalabilityRowsMatchColumnOrder() throws IOException {
        ResultsWriter results = new ResultsWriter(dir);
        results.saveRecovery("recovery_book_based",
            new RecoveryReport(100, 50, 50, 0, 0, Duration.ofMillis(5), Duration.ofMillis(7),
                Duration.ofMillis(12)));
        results.saveThroughput("write_throughput_book_based", 100, Duration.ofSeconds(5), 20.5);
        results.saveScalability("build_json_index", 25, new Measurement("build_json_index",
            Duration.ofSeconds(1), 2.0, 10.0));

        String recovery = Files.readString(dir.resolve("recovery.csv"), StandardCharsets.UTF_8);
        assertTrue(recovery.contains(
            "recovery_book_based,100,50,50,0,0,0.005000,0.007000,0.012000,"));
        String throughput = Files.readString(dir.resolve("throughput.csv"), StandardCharsets.UTF_8);
        assertTrue(throughput.contains("write_throughput_book_based,100,5.000000,20.5000,"));
        String scalability = Files.readString(dir.resolve("scalability.csv"), StandardCharsets.UTF_8);
        assertTrue(scalability.contains("build_json_index,25,1.000000,2.0000,10.00,"));
    }
}
