package datalake;

import java.nio.file.Path;

public record LocatedBook(Path bodyPath, Path headerPath) {
}
