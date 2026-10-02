package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

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
}
