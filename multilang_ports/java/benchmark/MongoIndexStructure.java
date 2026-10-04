package benchmark;

import datamarts.MongoIndex;
import datamarts.MongoStorageStats;
import inverted_index.Postings;
import java.io.IOException;
import java.util.List;
import java.util.Map;

final class MongoIndexStructure implements IndexStructure {

    private static final double BYTES_PER_MB = 1024.0 * 1024.0;

    private final Suite suite;
    private final MongoIndex index;

    MongoIndexStructure(Suite suite, MongoIndex index) {
        this.suite = suite;
        this.index = index;
    }

    @Override
    public String name() {
        return "mongo_index";
    }

    @Override
    public void reset() {
        index.clear();
    }

    @Override
    public void build(List<TokenizedBook> books) {
        index.save(Postings.build(TokenizedBook.toMap(books)));
    }

    @Override
    public void prepareQuery() {
    }

    @Override
    public List<Integer> queryPostings(String term) {
        return index.query(term);
    }

    @Override
    public void addBook(int bookId, List<String> tokens) {
        index.updateBook(bookId, tokens);
    }

    @Override
    public DiskUsage storageUsage() {
        MongoStorageStats stats = index.storageStats();
        Config config = suite.config();
        String path = config.mongoUri() + "/" + config.mongoDatabase() + "." + config.mongoCollection();
        return new DiskUsage(path, stats.storageBytes() / BYTES_PER_MB, 0, 0);
    }

    @Override
    public void close() {
        index.close();
    }
}
