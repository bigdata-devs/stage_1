package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.util.List;
import org.junit.jupiter.api.Test;

class IndexBenchmarkTest {

    @Test
    void batchSizesSortAndDeduplicateTheCorpusSize() {
        assertEquals(List.of(25, 50, 60, 250, 500, 1000, 5000, 10000),
            IndexBenchmark.buildBatchSizes(60));
        assertEquals(List.of(10, 25, 50, 250, 500, 1000, 5000, 10000),
            IndexBenchmark.buildBatchSizes(10));
        assertEquals(List.of(25, 50, 250, 500, 600, 1000, 5000, 10000),
            IndexBenchmark.buildBatchSizes(600));
    }

    @Test
    void subsetKeepsRealBooksAndFillsWithSyntheticOnes() {
        List<TokenizedBook> books = List.of(
            new TokenizedBook(84, List.of("a")),
            new TokenizedBook(1342, List.of("b")));

        List<TokenizedBook> subset = IndexBenchmark.buildSubset(books, 5);

        assertEquals(5, subset.size());
        assertEquals(84, subset.get(0).id());
        assertEquals(1342, subset.get(1).id());
        assertEquals(900000, subset.get(2).id());
        assertEquals(900002, subset.get(4).id());
        assertEquals(List.of("a"), subset.get(2).tokens());
        assertEquals(List.of("b"), subset.get(3).tokens());
    }

    @Test
    void subsetNeverExceedsTheCorpusWhenBatchIsSmaller() {
        List<TokenizedBook> books = List.of(new TokenizedBook(1, List.of("x")));

        assertEquals(1, IndexBenchmark.buildSubset(books, 1).size());
        assertTrue(IndexBenchmark.buildSubset(books, 1).get(0).id() == 1);
    }

    @Test
    void repetitionsShrinkForLargeBatches() {
        assertEquals(5, IndexBenchmark.buildRepetitions(25));
        assertEquals(5, IndexBenchmark.buildRepetitions(1000));
        assertEquals(3, IndexBenchmark.buildRepetitions(5000));
        assertEquals(2, IndexBenchmark.buildRepetitions(10000));
    }

    @Test
    void warmUpBuildsTheSmallestBatchOnce() throws IOException {
        RecordingStructure structure = new RecordingStructure();

        IndexBenchmark.warmUpStructure(structure, List.of(new TokenizedBook(1, List.of("x"))));

        assertEquals(1, structure.buildCalls);
        assertEquals(1, structure.lastBatchSize);
    }

    private static final class RecordingStructure implements IndexStructure {

        int buildCalls;
        int lastBatchSize;

        @Override
        public String name() {
            return "recording";
        }

        @Override
        public void reset() {
        }

        @Override
        public void build(List<TokenizedBook> books) {
            buildCalls++;
            lastBatchSize = books.size();
        }

        @Override
        public void prepareQuery() {
        }

        @Override
        public List<Integer> queryPostings(String term) {
            return List.of();
        }

        @Override
        public void addBook(int bookId, List<String> tokens) {
        }

        @Override
        public DiskUsage storageUsage() {
            return new DiskUsage("nowhere", 0, 0, 0);
        }
    }
}
