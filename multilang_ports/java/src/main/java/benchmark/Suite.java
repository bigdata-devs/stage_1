package benchmark;

import datalake.BatchBased;
import datalake.BookBased;
import datalake.Fetcher;
import datalake.GutenbergFetcher;
import datalake.DirectoryFetcher;
import datalake.Layout;
import datalake.TimeBased;
import datamarts.MongoIndex;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;

public final class Suite {

    static final double MICROSECONDS_PER_SECOND = 1_000_000.0;

    private final Config config;
    private final ResultsWriter results;

    public Suite(Config config) {
        this.config = config;
        this.results = new ResultsWriter(config.resultsDir());
    }

    Config config() {
        return config;
    }

    ResultsWriter results() {
        return results;
    }

    public void run() throws IOException {
        if (!config.skipDatalake()) {
            try {
                new DatalakeBenchmark(this).run();
            } catch (IOException exception) {
                throw new IOException("datalake benchmark: " + exception.getMessage(), exception);
            }
        }
        if (!config.skipIndex()) {
            try {
                new IndexBenchmark(this).run();
            } catch (IOException exception) {
                throw new IOException("index benchmark: " + exception.getMessage(), exception);
            }
        }
        Log.line("Results appended to %s", config.resultsDir());
    }

    Measurement measure(String name, Measure.Operation operation) throws IOException {
        Measurement measurement;
        try {
            measurement = Measure.measure(name, operation);
        } catch (IOException exception) {
            throw new IOException(name + ": " + exception.getMessage(), exception);
        }
        saveMeasurement(measurement);
        return measurement;
    }

    void saveMeasurement(Measurement measurement) throws IOException {
        Log.line("[%s] %.4fs | mem %.2f MB | cpu %.1f%%", measurement.name(), measurement.seconds(),
            measurement.memoryMb(), measurement.cpuPercent());
        results.saveMeasurement(measurement);
    }

    void recordThroughput(Measurement measurement, int itemCount) throws IOException {
        double itemsPerSecond = Measure.throughput(itemCount, measurement.elapsed());
        Log.line("[%s] throughput %.4f items/s", measurement.name(), itemsPerSecond);
        results.saveThroughput(measurement.name(), itemCount, measurement.elapsed(), itemsPerSecond);
    }

    void recordDiskUsage(Path path) throws IOException {
        DiskUsage usage = DiskUsage.measure(path);
        Log.line("[disk] %s: %.4f MB, %d files, %d dirs", usage.path(), usage.sizeMb(),
            usage.fileCount(), usage.dirCount());
        results.saveDiskUsage(usage);
    }

    void recordQueryStatistics(String testName, List<Duration> durations) throws IOException {
        Statistics statistics = Statistics.calculate(durations);
        Log.line("[%s] %d samples, mean %.3f us, stdev %.3f us", testName, statistics.iterations(),
            statistics.meanSeconds() * MICROSECONDS_PER_SECOND,
            statistics.stdevSeconds() * MICROSECONDS_PER_SECOND);
        results.saveStatistics(testName, statistics);
    }

    Path outputPath(String... parts) {
        Path output = config.outputDir();
        for (String part : parts) {
            output = output.resolve(part);
        }
        return output;
    }

    Fetcher fetcher() {
        if (!config.rawBooksDir().isEmpty()) {
            return new DirectoryFetcher(Path.of(config.rawBooksDir()));
        }
        return new GutenbergFetcher(config.gutenbergUrl());
    }

    MongoIndex connectMongo() {
        return MongoIndex.connect(config.mongoUri(), config.mongoDatabase(), config.mongoCollection());
    }

    static List<Layout> standardLayouts() {
        return List.of(new TimeBased(), new BookBased(), new BatchBased());
    }

    static List<Integer> firstIds(List<Integer> ids, int count) {
        if (count >= ids.size()) {
            return ids;
        }
        return List.copyOf(ids.subList(0, count));
    }

    static void resetDirectory(Path path) throws IOException {
        if (!Files.exists(path)) {
            return;
        }
        try (var paths = Files.walk(path)) {
            for (Path entry : paths.sorted(java.util.Comparator.reverseOrder()).toList()) {
                Files.delete(entry);
            }
        }
    }
}
