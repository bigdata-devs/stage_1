package benchmark;

import datalake.Datalake;
import datalake.Fetcher;
import datalake.Layout;
import datalake.TimeBased;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

final class DatalakeBenchmark {

    private static final int DOWNLOAD_PROBE_COUNT = 10;

    private final Suite suite;
    private final Config config;

    DatalakeBenchmark(Suite suite) {
        this.suite = suite;
        this.config = suite.config();
    }

    void run() throws IOException {
        for (Layout layout : Suite.standardLayouts()) {
            benchmarkLayout(layout);
        }
        measureDownloadProbe();
    }

    private void benchmarkLayout(Layout layout) throws IOException {
        Path root = suite.outputPath("datalake", layout.name());
        Datalake lake = new Datalake(root, layout);
        Suite.resetDirectory(root);
        measureLayoutWrite(layout, lake);
        measureLayoutLookup(layout, root);
        measureLayoutIncremental(layout, root);
        measureLayoutRecovery(layout, root);
        suite.recordDiskUsage(root);
    }

    private void measureLayoutWrite(Layout layout, Datalake lake) throws IOException {
        Measurement measurement = suite.measure("write_throughput_" + layout.name(),
            () -> populateFromCorpus(lake));
        suite.recordThroughput(measurement, config.bookIds().size());
    }

    private void populateFromCorpus(Datalake lake) throws IOException {
        for (int bookId : config.bookIds()) {
            String body = Files.readString(config.bodiesDir().resolve(bookId + "_body.txt"),
                StandardCharsets.UTF_8);
            String header = Files.readString(config.headersDir().resolve(bookId + "_header.txt"),
                StandardCharsets.UTF_8);
            lake.store(bookId, header, body);
        }
    }

    private void measureLayoutLookup(Layout layout, Path root) throws IOException {
        List<Duration> durations = new ArrayList<>(config.bookIds().size());
        for (int bookId : config.bookIds()) {
            long start = System.nanoTime();
            layout.locate(root, bookId);
            durations.add(Duration.ofNanos(System.nanoTime() - start));
        }
        suite.recordQueryStatistics("lookup_" + layout.name(), durations);
    }

    private void measureLayoutIncremental(Layout layout, Path root) throws IOException {
        List<Integer> known = Suite.firstIds(config.bookIds(), config.bookIds().size() / 2);
        suite.measure("incremental_" + layout.name(), () -> Datalake.pendingBookIds(root, known));
    }

    private void measureLayoutRecovery(Layout layout, Path root) throws IOException {
        RecoveryReport report = Recovery.resumeAfterInterruption(layout, root, config.bookIds());
        Log.line("[recovery_%s] %d resumed, %d duplicated, %d lost", layout.name(),
            report.processedAfter(), report.duplicated(), report.lost());
        suite.results().saveRecovery("recovery_" + layout.name(), report);
    }

    private void measureDownloadProbe() throws IOException {
        List<Integer> probeIds = Suite.firstIds(config.bookIds(), DOWNLOAD_PROBE_COUNT);
        if (probeIds.isEmpty()) {
            return;
        }
        Path probeRoot = suite.outputPath("datalake", "download_probe");
        Suite.resetDirectory(probeRoot);
        Fetcher fetcher = suite.fetcher();
        int[] stored = {0};
        Measurement measurement = Measure.measure("download_write_throughput",
            () -> stored[0] = downloadProbe(fetcher, probeIds, probeRoot));
        if (stored[0] == 0) {
            Log.line("[datalake] SKIP download_write_throughput: network unavailable");
            return;
        }
        suite.saveMeasurement(measurement);
        suite.recordThroughput(measurement, stored[0]);
    }

    private int downloadProbe(Fetcher fetcher, List<Integer> probeIds, Path probeRoot) {
        Datalake lake = new Datalake(probeRoot, new TimeBased());
        int stored = 0;
        for (int bookId : probeIds) {
            if (lake.download(fetcher, bookId)) {
                stored++;
            }
        }
        return stored;
    }
}
