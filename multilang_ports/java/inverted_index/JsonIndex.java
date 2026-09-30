package inverted_index;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

public final class JsonIndex {

    private JsonIndex() {
    }

    public static LinkedHashMap<String, List<Integer>> buildIndex(Map<Integer, List<String>> books) {
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

    public static void saveIndex(Map<String, List<Integer>> index, Path outputPath) throws IOException {
        Files.writeString(outputPath, serialize(index), StandardCharsets.UTF_8);
    }

    public static Map<String, List<Integer>> loadIndex(Path indexPath) throws IOException {
        String json = Files.readString(indexPath, StandardCharsets.UTF_8);
        return new IndexParser(json).parse();
    }

    private static String serialize(Map<String, List<Integer>> index) {
        StringBuilder json = new StringBuilder("{\n");
        List<Map.Entry<String, List<Integer>>> entries = new ArrayList<>(index.entrySet());
        for (int position = 0; position < entries.size(); position++) {
            Map.Entry<String, List<Integer>> entry = entries.get(position);
            json.append("  \"").append(entry.getKey()).append("\": ");
            appendPostings(json, entry.getValue());
            json.append(isLastEntry(entries, position) ? "\n" : ",\n");
        }
        return json.append("}").toString();
    }

    private static void appendPostings(StringBuilder json, List<Integer> bookIds) {
        if (bookIds.isEmpty()) {
            json.append("[]");
            return;
        }
        json.append("[\n");
        for (int position = 0; position < bookIds.size(); position++) {
            json.append("    ").append(bookIds.get(position));
            json.append(position < bookIds.size() - 1 ? ",\n" : "\n");
        }
        json.append("  ]");
    }

    private static boolean isLastEntry(List<Map.Entry<String, List<Integer>>> entries, int position) {
        return position == entries.size() - 1;
    }

    private static final class IndexParser {

        private final String source;
        private int position;

        IndexParser(String source) {
            this.source = source;
        }

        Map<String, List<Integer>> parse() {
            Map<String, List<Integer>> index = new HashMap<>();
            expect('{');
            skipWhitespace();
            if (peek() == '}') {
                return index;
            }
            while (true) {
                skipWhitespace();
                String term = parseString();
                skipWhitespace();
                expect(':');
                skipWhitespace();
                index.put(term, parsePostings());
                skipWhitespace();
                if (consumeIf('}')) {
                    return index;
                }
                expect(',');
            }
        }

        private List<Integer> parsePostings() {
            List<Integer> bookIds = new ArrayList<>();
            expect('[');
            skipWhitespace();
            if (peek() == ']') {
                position++;
                return bookIds;
            }
            while (true) {
                skipWhitespace();
                bookIds.add(parseInteger());
                skipWhitespace();
                if (consumeIf(']')) {
                    return bookIds;
                }
                expect(',');
            }
        }

        private String parseString() {
            expect('"');
            int start = position;
            while (source.charAt(position) != '"') {
                position++;
            }
            String value = source.substring(start, position);
            position++;
            return value;
        }

        private int parseInteger() {
            int start = position;
            while (Character.isDigit(source.charAt(position)) || source.charAt(position) == '-') {
                position++;
            }
            return Integer.parseInt(source.substring(start, position));
        }

        private void skipWhitespace() {
            while (position < source.length() && Character.isWhitespace(source.charAt(position))) {
                position++;
            }
        }

        private char peek() {
            return source.charAt(position);
        }

        private boolean consumeIf(char expected) {
            if (peek() == expected) {
                position++;
                return true;
            }
            return false;
        }

        private void expect(char expected) {
            char actual = source.charAt(position);
            if (actual != expected) {
                throw new IllegalStateException(
                    "Expected '" + expected + "' but found '" + actual + "' at position " + position);
            }
            position++;
        }
    }
}
