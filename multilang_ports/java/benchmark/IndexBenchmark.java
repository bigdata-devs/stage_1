package benchmark;

import datamarts.MongoIndex;
import inverted_index.Corpus;
import inverted_index.Postings;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

final class IndexBenchmark {

    private static final int SYNTHETIC_BOOK_ID_BASE = 900000;

    private final Suite suite;
    private final Config config;

    IndexBenchmark(Suite suite) {
        this.suite = suite;
        this.config = suite.config();
    }

    void run() throws IOException {
        List<TokenizedBook> books = measurePipelineStages();
        if (books.isEmpty()) {
            throw new IOException("index benchmark: no books in " + config.bodiesDir());
        }
        List<IndexStructure> structures = indexStructures();
        try {
            for (IndexStructure structure : structures) {
                try {
                    runStructureExperiments(structure, books);
                } catch (IOException exception) {
                    throw new IOException(structure.name() + " experiments: " + exception.getMessage(), exception);
                }
            }
        } finally {
            closeStructures(structures);
        }
    }

    private void runStructureExperiments(IndexStructure structure, List<TokenizedBook> books) throws IOException {
        Log.line("--- Inverted index structure: %s ---", structure.name());
        structure.reset();
        for (int batchSize : buildBatchSizes(books.size())) {
            measureBuildBatch(structure, buildSubset(books, batchSize), batchSize);
        }
        structure.prepareQuery();
        suite.recordQueryStatistics("query_" + structure.name(), runQueryWorkload(structure));
        measureStructureUpdate(structure, books);
        measureStructureStorage(structure);
    }

    private void measureBuildBatch(IndexStructure structure, List<TokenizedBook> batch, int batchSize)
            throws IOException {
        Measurement measurement = Measure.measure("build_" + structure.name(), () -> structure.build(batch));
        Log.line("[build_%s] batch %d: %.4fs", structure.name(), batchSize, measurement.seconds());
        suite.results().saveScalability("build_" + structure.name(), batchSize, measurement);
    }

    private void measureStructureUpdate(IndexStructure structure, List<TokenizedBook> books) throws IOException {
        int newBookId = books.get(books.size() - 1).id() + 1;
        List<String> tokens = books.get(0).tokens();
        suite.measure("update_" + structure.name(), () -> structure.addBook(newBookId, tokens));
    }

    private void measureStructureStorage(IndexStructure structure) throws IOException {
        DiskUsage usage = structure.storageUsage();
        Log.line("[disk] %s: %.4f MB, %d files, %d dirs", usage.path(), usage.sizeMb(),
            usage.fileCount(), usage.dirCount());
        suite.results().saveDiskUsage(usage);
    }

    private List<IndexStructure> indexStructures() throws IOException {
        List<IndexStructure> structures = new ArrayList<>();
        structures.add(new JsonIndexStructure(suite));
        structures.add(new FolderIndexStructure(suite));
        if (config.skipMongo() || !MongoIndex.isAvailable(config.mongoUri())) {
            Log.line("[mongo] MongoDB skipped (disabled or not reachable at %s)", config.mongoUri());
            return structures;
        }
        structures.add(new MongoIndexStructure(suite, suite.connectMongo()));
        return structures;
    }

    private static void closeStructures(List<IndexStructure> structures) {
        for (IndexStructure structure : structures) {
            try {
                structure.close();
            } catch (IOException exception) {
                Log.line("[index] close %s: %s", structure.name(), exception.getMessage());
            }
        }
    }

    static List<Integer> buildBatchSizes(int bookCount) {
        TreeSet<Integer> sizes = new TreeSet<>(List.of(25, 50, 250, 500, 1000, 5000, 10000));
        sizes.add(bookCount);
        return List.copyOf(sizes);
    }

    static List<TokenizedBook> buildSubset(List<TokenizedBook> books, int batchSize) {
        int realCount = Math.min(batchSize, books.size());
        List<TokenizedBook> subset = new ArrayList<>(batchSize);
        subset.addAll(books.subList(0, realCount));
        for (int offset = 0; offset < batchSize - realCount; offset++) {
            subset.add(new TokenizedBook(SYNTHETIC_BOOK_ID_BASE + offset,
                books.get(offset % books.size()).tokens()));
        }
        return List.copyOf(subset);
    }

    private List<TokenizedBook> measurePipelineStages() throws IOException {
        AtomicReference<List<TokenizedBook>> loaded = new AtomicReference<>(List.of());
        Measurement tokenize = suite.measure("tokenize_books", () -> loaded.set(loadCorpus()));
        List<TokenizedBook> books = loaded.get();
        Log.line("[index] %d books from %s", books.size(), config.bodiesDir());
        suite.recordThroughput(tokenize, books.size());
        AtomicInteger termCount = new AtomicInteger();
        suite.measure("build_postings", () -> termCount.set(Postings.build(TokenizedBook.toMap(books)).size()));
        Log.line("[index] %d unique terms", termCount.get());
        return books;
    }

    private List<TokenizedBook> loadCorpus() throws IOException {
        LinkedHashMap<Integer, List<String>> corpus = Corpus.load(config.bodiesDir());
        List<TokenizedBook> books = new ArrayList<>(corpus.size());
        for (Map.Entry<Integer, List<String>> book : corpus.entrySet()) {
            books.add(new TokenizedBook(book.getKey(), book.getValue()));
        }
        return books;
    }

    private List<Duration> runQueryWorkload(IndexStructure structure) throws IOException {
        List<Duration> durations =
            new ArrayList<>(config.queries().size() * config.queryRepetitions());
        for (int repetition = 0; repetition < config.queryRepetitions(); repetition++) {
            for (List<String> query : config.queries()) {
                long start = System.nanoTime();
                Queries.intersect(query, structure::queryPostings);
                durations.add(Duration.ofNanos(System.nanoTime() - start));
            }
        }
        return durations;
    }
}
