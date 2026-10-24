package microbench;

import inverted_index.Postings;
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
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;

/**
 * PostingsBenchmark measures the in-memory construction of the inverted index
 * (the postings map) for a growing number of books, isolating it from any
 * serialization or storage cost, which the harness already measures end to end.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
@State(Scope.Benchmark)
public class PostingsBenchmark {

    @Param({"10", "100"})
    public int bookCount;

    private Map<Integer, List<String>> books;

    @Setup(Level.Trial)
    public void setUp() {
        books = SampleBook.sampleTokenizedBooks(bookCount);
    }

    @Benchmark
    public Map<String, List<Integer>> buildPostings() {
        return Postings.build(books);
    }
}
