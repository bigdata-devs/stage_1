package microbench;

import inverted_index.TextProcessor;
import java.util.List;
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
 * TokenizeBenchmark measures the text-processor step alone (tokenize plus
 * normalize) on one book-sized input. JMH supplies the protocol: warm-up
 * iterations, forks and error estimation. These numbers are Java-only
 * micro-evidence and must never be mixed with harness rows of other languages.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(1)
@State(Scope.Benchmark)
public class TokenizeBenchmark {

    private String bookText;

    @Setup(Level.Trial)
    public void setUp() {
        bookText = SampleBook.sampleBookText();
    }

    @Benchmark
    public List<String> tokenizeBook() {
        return TextProcessor.processText(bookText);
    }
}
