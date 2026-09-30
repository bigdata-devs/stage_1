package datamarts;

import inverted_index.Postings;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class FolderIndex {

    private static final String FILE_EXTENSION = ".txt";

    private FolderIndex() {
    }

    public static void save(Map<String, List<Integer>> index, Path outputDir) throws IOException {
        Files.createDirectories(outputDir);
        Set<Path> createdLetters = new HashSet<>();
        for (Map.Entry<String, List<Integer>> entry : index.entrySet()) {
            Path letterDir = outputDir.resolve(letter(entry.getKey()));
            if (createdLetters.add(letterDir)) {
                Files.createDirectories(letterDir);
            }
            writeTermFile(termFile(letterDir, entry.getKey()), entry.getValue());
        }
    }

    public static List<Integer> query(String term, Path indexDir) throws IOException {
        if (term.isEmpty()) {
            return List.of();
        }
        Path file = termFile(indexDir.resolve(letter(term)), term);
        if (!Files.isRegularFile(file)) {
            return List.of();
        }
        return readPostings(file);
    }

    public static void update(int bookId, List<String> tokens, Path indexDir) throws IOException {
        for (String term : Postings.uniqueTerms(tokens)) {
            Path letterDir = indexDir.resolve(letter(term));
            Files.createDirectories(letterDir);
            Path file = termFile(letterDir, term);
            List<Integer> postings = Files.isRegularFile(file) ? readPostings(file) : List.of();
            writeTermFile(file, Postings.appendSortedUnique(postings, bookId));
        }
    }

    private static String letter(String term) {
        return String.valueOf(Character.toUpperCase(term.charAt(0)));
    }

    private static Path termFile(Path letterDir, String term) {
        return letterDir.resolve(term + FILE_EXTENSION);
    }

    private static List<Integer> readPostings(Path file) throws IOException {
        List<Integer> bookIds = new ArrayList<>();
        for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
            String trimmed = line.trim();
            if (!trimmed.isEmpty()) {
                bookIds.add(Integer.parseInt(trimmed));
            }
        }
        return bookIds;
    }

    private static void writeTermFile(Path file, List<Integer> bookIds) throws IOException {
        StringBuilder content = new StringBuilder();
        for (int bookId : bookIds) {
            content.append(bookId).append('\n');
        }
        Files.writeString(file, content.toString(), StandardCharsets.UTF_8);
    }
}
