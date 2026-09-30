package datalake;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

public interface Layout {

    String BODY_SUFFIX = "_body.txt";
    String HEADER_SUFFIX = "_header.txt";

    static Path defaultRoot() {
        return Paths.get(".").toAbsolutePath().normalize().resolve("datalake");
    }

    String name();

    Path directory(Path root, int bookId);

    LocatedBook locate(Path root, int bookId) throws IOException;
}
