package inverted_index;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

public final class Main {

    private Main() {
    }

    public static void main(String[] args) {
        try {
            run(args);
        } catch (IOException | RuntimeException exception) {
            System.err.println(exception.getMessage());
            System.exit(1);
        }
    }

    private static void run(String[] args) throws IOException {
        if (args.length == 3 && args[0].equals("build")) {
            buildIndex(Path.of(args[1]), Path.of(args[2]));
        } else if (args.length >= 3 && args[0].equals("query")) {
            queryTerms(Path.of(args[1]), Arrays.copyOfRange(args, 2, args.length));
        } else {
            printUsage();
            System.exit(1);
        }
    }

    private static void buildIndex(Path bodiesDirectory, Path outputPath) throws IOException {
        Map<String, List<Integer>> index = JsonIndex.buildIndex(Corpus.load(bodiesDirectory));
        JsonIndex.saveIndex(index, outputPath);
        System.out.println("Index contains " + index.size() + " unique terms");
    }

    private static void queryTerms(Path indexPath, String[] terms) throws IOException {
        Map<String, List<Integer>> index = JsonIndex.loadIndex(indexPath);
        for (String term : terms) {
            System.out.println(term + ": " + index.getOrDefault(term, List.of()));
        }
    }

    private static void printUsage() {
        System.err.println("Usage: java inverted_index.Main build <bodies_dir> <output_json>");
        System.err.println("       java inverted_index.Main query <index_json> <term>...");
    }
}
