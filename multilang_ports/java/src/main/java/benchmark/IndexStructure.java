package benchmark;

import java.io.IOException;
import java.util.List;

interface IndexStructure {

    String name();

    void reset() throws IOException;

    void build(List<TokenizedBook> books) throws IOException;

    void prepareQuery() throws IOException;

    List<Integer> queryPostings(String term) throws IOException;

    void addBook(int bookId, List<String> tokens) throws IOException;

    default void releaseQueryCache() {
    }

    DiskUsage storageUsage() throws IOException;

    default void close() throws IOException {
    }
}
