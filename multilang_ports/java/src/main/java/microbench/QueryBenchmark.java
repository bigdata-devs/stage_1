package microbench;

import benchmark.Queries;
import inverted_index.Postings;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
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
import org.openjdk.jmh.annotations.Warmup;

/**
 * QueryBenchmark measures the in-memory query path of the shared workload:
 * intersecting the posting lists of every query term, using the repository
 * queries.txt so the micro workload matches the harness workload.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
@State(Scope.Benchmark)
public class QueryBenchmark {

    private static final String QUERIES_PATH_PROPERTY = "jmh.queries.path";
    private static final String DEFAULT_QUERIES_PATH = "src/utils/benchmarks/queries.txt";

    private Map<String, List<Integer>> index;
    private List<List<String>> queries;
    private int cursor;

    @Setup(Level.Trial)
    public void setUp() {
        index = Postings.build(SampleBook.sampleTokenizedBooks(50));
        queries = representativeQueries();
    }

    @Benchmark
    public List<Integer> intersectQuery() throws IOException {
        List<String> query = queries.get(cursor);
        cursor = (cursor + 1) % queries.size();
        return Queries.intersect(query, term -> index.getOrDefault(term, List.of()));
    }

    private List<List<String>> representativeQueries() {
        List<List<String>> repositoryQueries =
            loadQueries(Path.of(System.getProperty(QUERIES_PATH_PROPERTY, DEFAULT_QUERIES_PATH)));
        if (!repositoryQueries.isEmpty()) {
            return repositoryQueries;
        }
        return fallbackQueries();
    }

    private static List<List<String>> loadQueries(Path path) {
        try {
            return Queries.load(path);
        } catch (IOException exception) {
            return List.of();
        }
    }

    /** fallbackQueries pairs consecutive frequent terms of the sample index
     * when the repository query file is not reachable from the working
     * directory. */
    private List<List<String>> fallbackQueries() {
        List<String> terms = new ArrayList<>(index.keySet().stream().limit(40).toList());
        List<List<String>> fallback = new ArrayList<>();
        for (int position = 0; position + 1 < terms.size(); position += 2) {
            fallback.add(List.of(terms.get(position), terms.get(position + 1)));
        }
        if (fallback.isEmpty()) {
            fallback.add(List.of());
        }
        return fallback;
    }
}
