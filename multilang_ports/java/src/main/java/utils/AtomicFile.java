package utils;

import java.io.IOException;
import java.io.Writer;
import java.nio.channels.Channels;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Set;

/**
 * Crash-safe file replacement: readers see either the old file or the complete new one.
 *
 * <p>The content is produced into a temporary sibling that starts with a dot and ends in
 * {@code .tmp}, so the datalake and index globs never mistake it for a real book or term file.
 * The temporary file is forced to stable storage with {@code fsync} and then swapped in with an
 * atomic move, which is what {@code write_text_atomically()} does in the Python baseline.
 */
public final class AtomicFile {

    private static final String TEMPORARY_SUFFIX = ".tmp";
    private static final Set<PosixFilePermission> FILE_PERMISSIONS =
        PosixFilePermissions.fromString("rw-r--r--");

    private AtomicFile() {
    }

    /** Writes UTF-8 text with the durability of {@link #write(Path, Body)}. */
    public static void writeText(Path target, String content) throws IOException {
        write(target, writer -> writer.write(content));
    }

    /** Produces the file through the caller's writer, then fsyncs and renames it into place. */
    public static void write(Path target, Body body) throws IOException {
        Path directory = target.getParent() != null ? target.getParent() : Path.of(".");
        Files.createDirectories(directory);
        Path temporary = Files.createTempFile(directory, "." + target.getFileName() + ".",
            TEMPORARY_SUFFIX, PosixFilePermissions.asFileAttribute(FILE_PERMISSIONS));
        try {
            produce(temporary, body);
            Files.move(temporary, target, StandardCopyOption.REPLACE_EXISTING,
                StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException | RuntimeException exception) {
            Files.deleteIfExists(temporary);
            throw exception;
        }
    }

    private static void produce(Path temporary, Body body) throws IOException {
        try (FileChannel channel = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
            Writer writer = Channels.newWriter(channel, StandardCharsets.UTF_8.newEncoder(), 8192);
            body.writeTo(writer);
            writer.flush();
            channel.force(true);
        }
    }

    /** One step of the file production, so callers can stream instead of building a string. */
    @FunctionalInterface
    public interface Body {

        void writeTo(Writer writer) throws IOException;
    }
}
