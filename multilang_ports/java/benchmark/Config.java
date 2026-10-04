package benchmark;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import inverted_index.Corpus;

public record Config(List<Integer> bookIds, String rawBooksDir, String gutenbergUrl, Path bodiesDir,
        Path headersDir, Path outputDir, Path resultsDir, String mongoUri, String mongoDatabase,
        String mongoCollection, List<List<String>> queries, int queryRepetitions, boolean skipDatalake,
        boolean skipIndex, boolean skipMongo) {

    public static final String DEFAULT_BODIES_DIR = "../../data_source/bodies";
    public static final String DEFAULT_HEADERS_DIR = "../../data_source/headers";
    public static final String DEFAULT_QUERIES_PATH = "../../src/utils/benchmarks/queries.txt";
    public static final String DEFAULT_GUTENBERG_URL = "https://www.gutenberg.org/cache/epub";
    public static final String DEFAULT_MONGO_URI = "mongodb://localhost:27017";
    public static final String DEFAULT_MONGO_DATABASE = "search_engine_benchmark";
    public static final String DEFAULT_MONGO_COLLECTION = "inverted_index";

    private static final Set<String> BOOLEAN_FLAGS = Set.of("-skip-datalake", "-skip-index", "-skip-mongo");
    private static final String BOOLEAN_FLAG_VALUE = "true";

    public static Config parse(String[] args) throws IOException {
        Map<String, String> flags = parseFlags(args);
        int queryRepetitions = Integer.parseInt(flags.getOrDefault("-query-repetitions", "5"));
        if (queryRepetitions < 1) {
            throw new IllegalArgumentException("-query-repetitions must be at least 1");
        }
        String bodiesDir = flags.getOrDefault("-bodies", DEFAULT_BODIES_DIR);
        List<List<String>> queries = Queries.load(Path.of(flags.getOrDefault("-queries", DEFAULT_QUERIES_PATH)));
        return new Config(
            bookIds(flags.getOrDefault("-ids", ""), Path.of(bodiesDir)),
            flags.getOrDefault("-raw-dir", ""),
            flags.getOrDefault("-gutenberg-url", DEFAULT_GUTENBERG_URL),
            Path.of(bodiesDir),
            Path.of(flags.getOrDefault("-headers", DEFAULT_HEADERS_DIR)),
            Path.of(flags.getOrDefault("-out", defaultArtifactDir())),
            Path.of(flags.getOrDefault("-results", "results")),
            flags.getOrDefault("-mongo-uri", DEFAULT_MONGO_URI),
            flags.getOrDefault("-mongo-db", DEFAULT_MONGO_DATABASE),
            flags.getOrDefault("-mongo-collection", DEFAULT_MONGO_COLLECTION),
            queries,
            queryRepetitions,
            flags.containsKey("-skip-datalake"),
            flags.containsKey("-skip-index"),
            flags.containsKey("-skip-mongo"));
    }

    private static Map<String, String> parseFlags(String[] args) {
        Map<String, String> flags = new LinkedHashMap<>();
        for (int position = 0; position < args.length; position++) {
            String argument = args[position];
            int equals = argument.indexOf('=');
            if (equals >= 0) {
                flags.put(argument.substring(0, equals), argument.substring(equals + 1));
            } else if (BOOLEAN_FLAGS.contains(argument)) {
                flags.put(argument, BOOLEAN_FLAG_VALUE);
            } else {
                position++;
                flags.put(argument, valueAt(args, position, argument));
            }
        }
        return flags;
    }

    private static String valueAt(String[] args, int position, String flagName) {
        if (position >= args.length) {
            throw new IllegalArgumentException("missing value for " + flagName);
        }
        return args[position];
    }

    private static List<Integer> bookIds(String flagValue, Path bodiesDir) throws IOException {
        if (flagValue.isEmpty()) {
            return Corpus.discoverBookIds(bodiesDir);
        }
        List<Integer> ids = new ArrayList<>();
        for (String item : flagValue.split(",")) {
            String trimmed = item.trim();
            if (!trimmed.isEmpty()) {
                ids.add(Integer.parseInt(trimmed));
            }
        }
        return List.copyOf(ids);
    }

    private static String defaultArtifactDir() {
        return Path.of(System.getProperty("user.home"), ".cache", "stage_1_benchmarks", "java").toString();
    }
}
