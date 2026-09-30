package inverted_index;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class PostingsTest {

    @Test
    void buildSortsAndDeduplicatesBookIds() {
        Map<Integer, List<String>> books = new LinkedHashMap<>();
        books.put(9, List.of("cat"));
        books.put(3, List.of("cat"));
        books.put(9, List.of("cat"));
        Map<String, List<Integer>> index = Postings.build(books);
        assertEquals(List.of(3, 9), index.get("cat"));
    }

    @Test
    void buildKeepsFirstAppearanceOrderOfTerms() {
        Map<Integer, List<String>> books = new LinkedHashMap<>();
        books.put(1, List.of("zebra", "apple"));
        books.put(2, List.of("mango", "apple"));
        assertEquals(List.of("zebra", "apple", "mango"), List.copyOf(Postings.build(books).keySet()));
    }

    @Test
    void uniqueTermsKeepsFirstAppearance() {
        assertEquals(List.of("cat", "dog", "bird"),
            Postings.uniqueTerms(List.of("cat", "dog", "cat", "bird", "dog")));
    }

    @Test
    void appendSortedUniqueInsertsInOrderWithoutDuplicates() {
        assertEquals(List.of(5, 9, 12), Postings.appendSortedUnique(List.of(5, 12), 9));
        assertEquals(List.of(5, 12), Postings.appendSortedUnique(List.of(5, 12), 5));
        assertEquals(List.of(7), Postings.appendSortedUnique(List.of(), 7));
    }

    @Test
    void buildIndexOfCorpusStyleInputMatchesPythonSemantics() {
        Map<Integer, List<String>> books = new LinkedHashMap<>();
        books.put(11, List.of("island"));
        books.put(84, List.of("island", "shipwreck"));
        Map<String, List<Integer>> index = Postings.build(books);
        assertEquals(List.of(11, 84), index.get("island"));
        assertEquals(List.of(84), index.get("shipwreck"));
        assertTrue(index.keySet().stream().toList().indexOf("island") < index.keySet().stream().toList().indexOf("shipwreck"));
    }
}
