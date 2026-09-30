package benchmark;

import inverted_index.JsonIndex;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

final class JsonIndexStructure implements IndexStructure {

    private final Suite suite;
    private Map<String, List<Integer>> loaded = Map.of();

    JsonIndexStructure(Suite suite) {
        this.suite = suite;
    }

    @Override
    public String name() {
        return "json_index";
    }

    private Path path() {
        return suite.outputPath("datamarts", "inverted_index.json");
    }

    @Override
    public void reset() throws IOException {
        loaded = Map.of();
        Files.deleteIfExists(path());
    }

    @Override
    public void build(List<TokenizedBook> books) throws IOException {
        JsonIndex.saveIndex(JsonIndex.buildIndex(TokenizedBook.toMap(books)), path());
    }

    @Override
    public void prepareQuery() throws IOException {
        Path indexPath = path();
        suite.measure("load_json_index", () -> loaded = JsonIndex.loadIndex(indexPath));
    }

    @Override
    public List<Integer> queryPostings(String term) {
        return loaded.getOrDefault(term, List.of());
    }

    @Override
    public void addBook(int bookId, List<String> tokens) throws IOException {
        JsonIndex.addBook(bookId, tokens, path());
    }

    @Override
    public DiskUsage storageUsage() throws IOException {
        return DiskUsage.measure(path());
    }
}
