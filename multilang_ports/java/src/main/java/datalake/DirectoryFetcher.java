package datalake;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class DirectoryFetcher implements Fetcher {

    private final Path directory;

    public DirectoryFetcher(Path directory) {
        this.directory = directory;
    }

    @Override
    public String fetch(int bookId) throws IOException {
        return Files.readString(directory.resolve("pg" + bookId + ".txt"), StandardCharsets.UTF_8);
    }
}
