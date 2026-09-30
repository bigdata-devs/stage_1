package benchmark;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class Queries {

    private Queries() {
    }

    public static List<List<String>> load(Path path) throws IOException {
        List<List<String>> queries = new ArrayList<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            List<String> terms = termsOf(line);
            if (!terms.isEmpty()) {
                queries.add(terms);
            }
        }
        if (queries.isEmpty()) {
            throw new IOException(path + " must define at least one query");
        }
        return queries;
    }

    private static List<String> termsOf(String line) {
        String content = line;
        int comment = content.indexOf('#');
        if (comment >= 0) {
            content = content.substring(0, comment);
        }
        content = content.trim();
        if (content.isEmpty()) {
            return List.of();
        }
        return List.of(content.split("\\s+"));
    }

    public static List<Integer> intersect(List<String> terms, Lookup lookup) throws IOException {
        if (terms.isEmpty()) {
            return List.of();
        }
        Set<Integer> matched = null;
        for (int position = 0; position < terms.size(); position++) {
            Set<Integer> current = new HashSet<>(lookup.apply(terms.get(position)));
            if (position == 0) {
                matched = current;
            } else {
                matched.retainAll(current);
            }
            if (matched.isEmpty()) {
                break;
            }
        }
        List<Integer> result = new ArrayList<>(matched);
        result.sort(null);
        return result;
    }

    @FunctionalInterface
    public interface Lookup {
        List<Integer> apply(String term) throws IOException;
    }
}
