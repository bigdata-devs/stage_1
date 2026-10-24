package benchmark;

import datamarts.FolderIndex;
import inverted_index.Postings;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

final class FolderIndexStructure implements IndexStructure {

    private final Suite suite;

    FolderIndexStructure(Suite suite) {
        this.suite = suite;
    }

    @Override
    public String name() {
        return "folder_index";
    }

    private Path path() {
        return suite.outputPath("datamarts", "inverted_index");
    }

    @Override
    public void reset() throws IOException {
        Suite.resetDirectory(path());
    }

    @Override
    public void build(List<TokenizedBook> books) throws IOException {
        Map<String, List<Integer>> index = Postings.build(TokenizedBook.toMap(books));
        FolderIndex.save(index, path());
    }

    @Override
    public void prepareQuery() {
    }

    @Override
    public List<Integer> queryPostings(String term) throws IOException {
        return FolderIndex.query(term, path());
    }

    @Override
    public void addBook(int bookId, List<String> tokens) throws IOException {
        FolderIndex.update(bookId, tokens, path());
    }

    @Override
    public DiskUsage storageUsage() throws IOException {
        return DiskUsage.measure(path());
    }
}
