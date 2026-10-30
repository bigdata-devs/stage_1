package microbench;

import inverted_index.JsonIndex;
import inverted_index.Postings;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.TearDown;
import org.openjdk.jmh.annotations.Warmup;

/**
 * JsonIndexBenchmark splits the monolithic-file index phase into its two hot
 * paths: serializing the postings map to disk and parsing it back, so the
 * report can attribute the json_index costs to the right step.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
@State(Scope.Benchmark)
public class JsonIndexBenchmark {

    private Map<String, List<Integer>> index;
    private Path indexPath;

    @Setup(Level.Trial)
    public void setUp() throws IOException {
        index = Postings.build(SampleBook.sampleTokenizedBooks(50));
        indexPath = outputPath();
        Files.createDirectories(indexPath.getParent());
        JsonIndex.saveIndex(index, indexPath);
    }

    @TearDown(Level.Trial)
    public void tearDown() throws IOException {
        Files.deleteIfExists(indexPath);
    }

    @Benchmark
    public Path serializeIndex() throws IOException {
        JsonIndex.saveIndex(index, indexPath);
        return indexPath;
    }

    @Benchmark
    public Map<String, List<Integer>> parseIndex() throws IOException {
        return JsonIndex.loadIndex(indexPath);
    }

    private static Path outputPath() {
        return Path.of(System.getProperty("jmh.tmp.dir", "multilang_ports/java/target/jmh"),
            "micro_index.json");
    }
}
