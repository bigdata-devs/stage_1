package benchmark;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record TokenizedBook(int id, List<String> tokens) {

    public static LinkedHashMap<Integer, List<String>> toMap(List<TokenizedBook> books) {
        LinkedHashMap<Integer, List<String>> map = new LinkedHashMap<>();
        for (TokenizedBook book : books) {
            map.put(book.id(), book.tokens());
        }
        return map;
    }
}
