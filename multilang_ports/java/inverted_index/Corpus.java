package inverted_index;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

public final class Corpus {

    public static final String BODY_SUFFIX = "_body.txt";

    private Corpus() {
    }

    public static LinkedHashMap<Integer, List<String>> load(Path bodiesDirectory) throws IOException {
        LinkedHashMap<Integer, List<String>> books = new LinkedHashMap<>();
        for (int bookId : discoverBookIds(bodiesDirectory)) {
            Path bodyPath = bodiesDirectory.resolve(bookId + BODY_SUFFIX);
            String text = Files.readString(bodyPath, StandardCharsets.UTF_8);
            books.put(bookId, TextProcessor.processText(text));
        }
        return books;
    }

    public static List<Integer> discoverBookIds(Path bodiesDirectory) throws IOException {
        try (Stream<Path> files = Files.list(bodiesDirectory)) {
            return files.filter(Files::isRegularFile)
                .map(path -> path.getFileName().toString())
                .filter(name -> name.endsWith(BODY_SUFFIX))
                .map(name -> name.substring(0, name.length() - BODY_SUFFIX.length()))
                .filter(Corpus::isNumeric)
                .map(Integer::parseInt)
                .sorted()
                .toList();
        }
    }

    private static boolean isNumeric(String value) {
        return !value.isEmpty() && value.chars().allMatch(Character::isDigit);
    }
}
