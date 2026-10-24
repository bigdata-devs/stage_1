package microbench;

import inverted_index.TextProcessor;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * SampleBook builds the fixed inputs of the JMH micro-benchmarks. It prefers
 * the repository sample dataset (data_source/bodies) so the micro numbers use
 * the same books as the cross-language harness, and falls back to a fixed
 * embedded text so the suite also runs on machines without the dataset.
 */
public final class SampleBook {

    private static final String BODIES_DIRECTORY_PROPERTY = "jmh.bodies.dir";
    private static final String DEFAULT_BODIES_DIRECTORY = "data_source/bodies";
    private static final String FALLBACK_CHAPTER =
        "The ship lay at anchor in the quiet bay while the crew prepared the "
        + "longboats for the morning expedition. Beyond the reef the open sea "
        + "stretched to the horizon, and the old captain measured the distance "
        + "with a weathered sextangle, keeping every reading in his leather "
        + "notebook. Adventure, he often said, is only careful preparation "
        + "meeting an uncertain shore, and he repeated the motto whenever the "
        + "island bells announced the turning tide. The settlers traded "
        + "spices, timber and stories with the merchants who arrived each "
        + "season, and every conversation carried news from distant harbours. ";

    private SampleBook() {
    }

    /** sampleBookText returns one book-sized text: the first body file of the
     * sample dataset when it is reachable, otherwise the embedded chapter. */
    public static String sampleBookText() {
        return firstBodyFromDataset(bodiesDirectory()).orElseGet(SampleBook::embeddedText);
    }

    /** sampleTokenizedBooks returns bookCount books whose tokens come from the
     * sample dataset, or from the embedded chapter repeated when it is absent. */
    public static Map<Integer, List<String>> sampleTokenizedBooks(int bookCount) {
        List<List<String>> tokenizedBooks = tokenizedDatasetBooks(bookCount);
        if (tokenizedBooks.size() < bookCount) {
            List<String> fallbackTokens = TextProcessor.processText(sampleBookText());
            tokenizedBooks = new ArrayList<>();
            for (int index = 0; index < bookCount; index++) {
                tokenizedBooks.add(fallbackTokens);
            }
        }
        Map<Integer, List<String>> books = new LinkedHashMap<>();
        for (int index = 0; index < bookCount; index++) {
            books.put(index + 1, tokenizedBooks.get(index));
        }
        return books;
    }

    private static String bodiesDirectory() {
        return System.getProperty(BODIES_DIRECTORY_PROPERTY, DEFAULT_BODIES_DIRECTORY);
    }

    private static Optional<String> firstBodyFromDataset(String directory) {
        try (Stream<Path> bodies = bodyFiles(Path.of(directory))) {
            Optional<Path> firstBody = bodies.min(Comparator.comparing(Path::toString));
            if (firstBody.isEmpty()) {
                return Optional.empty();
            }
            return Optional.of(Files.readString(firstBody.get(), StandardCharsets.UTF_8));
        } catch (IOException | InvalidPathException exception) {
            return Optional.empty();
        }
    }

    private static Stream<Path> bodyFiles(Path directory) throws IOException {
        if (!Files.isDirectory(directory)) {
            return Stream.empty();
        }
        return Files.list(directory)
            .filter(path -> path.getFileName().toString().endsWith("_body.txt"));
    }

    private static List<List<String>> tokenizedDatasetBooks(int bookCount) {
        try (Stream<Path> bodies = bodyFiles(Path.of(bodiesDirectory()))) {
            return bodies.sorted(Comparator.comparing(Path::toString))
                .limit(bookCount)
                .map(SampleBook::tokenizeFile)
                .toList();
        } catch (IOException | InvalidPathException exception) {
            return List.of();
        }
    }

    private static List<String> tokenizeFile(Path body) {
        try {
            return TextProcessor.processText(Files.readString(body, StandardCharsets.UTF_8));
        } catch (IOException exception) {
            throw new UncheckedIOException(exception);
        }
    }

    private static String embeddedText() {
        StringBuilder text = new StringBuilder(FALLBACK_CHAPTER.length() * 220);
        for (int repeat = 0; repeat < 220; repeat++) {
            text.append(FALLBACK_CHAPTER);
        }
        return text.toString();
    }
}
