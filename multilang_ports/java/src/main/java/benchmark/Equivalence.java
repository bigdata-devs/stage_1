package benchmark;

import inverted_index.Postings;
import inverted_index.TextProcessor;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Equivalence writes the canonical file that the cross-language checker
 * compares byte for byte: the token stream of every sample book, the posting
 * lists built from them and the result of every shared query. It reuses the
 * exact tokenizer, postings builder and query intersection of the timed
 * suite, so a file identical to the other languages' proves the harness
 * measures the same work everywhere.
 */
public final class Equivalence {

    private Equivalence() {
    }

    public static void run(Path bodiesDirectory, Path bookIdsFile, Path queriesFile,
                           Path outputFile) throws IOException {
        List<Integer> bookIds = loadBookIds(bookIdsFile);
        Map<Integer, List<String>> tokenized = tokenizeBooks(bodiesDirectory, bookIds);
        Map<String, List<Integer>> index = Postings.build(tokenized);
        writeCanonicalFile(outputFile, tokenized, index, Queries.load(queriesFile));
    }

    static List<Integer> loadBookIds(Path bookIdsFile) throws IOException {
        List<Integer> bookIds = new ArrayList<>();
        for (String line : Files.readAllLines(bookIdsFile, StandardCharsets.UTF_8)) {
            if (!line.isBlank()) {
                bookIds.add(Integer.parseInt(line.strip()));
            }
        }
        return bookIds;
    }

    static Map<Integer, List<String>> tokenizeBooks(Path bodiesDirectory,
                                                    List<Integer> bookIds) throws IOException {
        Map<Integer, List<String>> tokenized = new LinkedHashMap<>();
        for (int bookId : bookIds) {
            Path body = bodiesDirectory.resolve(bookId + "_body.txt");
            tokenized.put(bookId, TextProcessor.processText(Files.readString(body)));
        }
        return tokenized;
    }

    static void writeCanonicalFile(Path outputFile, Map<Integer, List<String>> tokenized,
                                   Map<String, List<Integer>> index,
                                   List<List<String>> queries) throws IOException {
        Files.createDirectories(outputFile.toAbsolutePath().getParent());
        try (BufferedWriter writer = Files.newBufferedWriter(outputFile, StandardCharsets.UTF_8)) {
            writeTokenLines(writer, tokenized);
            writePostingsLines(writer, index);
            writeQueryLines(writer, queries, index);
        }
    }

    private static void writeTokenLines(BufferedWriter writer,
                                        Map<Integer, List<String>> tokenized) throws IOException {
        for (Map.Entry<Integer, List<String>> book : tokenized.entrySet()) {
            writer.write("tokens\t" + book.getKey() + "\t" + String.join("\t", book.getValue()));
            writer.write("\n");
        }
    }

    private static void writePostingsLines(BufferedWriter writer,
                                           Map<String, List<Integer>> index) throws IOException {
        for (Map.Entry<String, List<Integer>> entry : new TreeMap<>(index).entrySet()) {
            writer.write("postings\t" + entry.getKey() + "\t" + formatIds(entry.getValue()));
            writer.write("\n");
        }
    }

    private static void writeQueryLines(BufferedWriter writer, List<List<String>> queries,
                                        Map<String, List<Integer>> index) throws IOException {
        int ordinal = 0;
        for (List<String> terms : queries) {
            ordinal++;
            List<Integer> matched;
            try {
                matched = Queries.intersect(terms, term -> index.getOrDefault(term, List.of()));
            } catch (IOException exception) {
                throw new IOException("query " + ordinal + " failed: " + exception.getMessage(),
                    exception);
            }
            String suffix = matched.isEmpty() ? "" : "\t" + formatIds(matched);
            writer.write("query\t" + ordinal + suffix);
            writer.write("\n");
        }
    }

    private static String formatIds(List<Integer> bookIds) {
        List<String> formatted = new ArrayList<>(bookIds.size());
        for (int bookId : bookIds) {
            formatted.add(Integer.toString(bookId));
        }
        return String.join(",", formatted);
    }
}
