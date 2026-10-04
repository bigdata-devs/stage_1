package inverted_index;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

public final class Postings {

    private Postings() {
    }

    public static LinkedHashMap<String, List<Integer>> build(Map<Integer, List<String>> books) {
        LinkedHashMap<String, TreeSet<Integer>> postings = new LinkedHashMap<>();
        for (Map.Entry<Integer, List<String>> book : books.entrySet()) {
            for (String token : book.getValue()) {
                postings.computeIfAbsent(token, key -> new TreeSet<>()).add(book.getKey());
            }
        }
        LinkedHashMap<String, List<Integer>> index = new LinkedHashMap<>();
        postings.forEach((term, bookIds) -> index.put(term, new ArrayList<>(bookIds)));
        return index;
    }

    public static List<String> uniqueTerms(List<String> tokens) {
        LinkedHashMap<String, Boolean> seen = new LinkedHashMap<>();
        for (String token : tokens) {
            seen.putIfAbsent(token, Boolean.TRUE);
        }
        return new ArrayList<>(seen.keySet());
    }

    public static List<Integer> appendSortedUnique(List<Integer> bookIds, int bookId) {
        int index = 0;
        while (index < bookIds.size() && bookIds.get(index) < bookId) {
            index++;
        }
        if (index < bookIds.size() && bookIds.get(index) == bookId) {
            return bookIds;
        }
        List<Integer> updated = new ArrayList<>(bookIds);
        updated.add(index, bookId);
        return updated;
    }
}
