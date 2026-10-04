package benchmark;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.stream.Stream;
import com.sun.management.OperatingSystemMXBean;

public final class Measure {

    private static final double BYTES_PER_MB = 1024.0 * 1024.0;

    private Measure() {
    }

    public static Measurement measure(String name, Operation operation) throws IOException {
        long memoryBefore = rssBytes();
        long cpuBefore = processCpuTimeNanos();
        long start = System.nanoTime();

        operation.run();

        Duration elapsed = Duration.ofNanos(System.nanoTime() - start);
        long memoryAfter = rssBytes();
        long cpuUsed = processCpuTimeNanos() - cpuBefore;
        double memoryMb = Math.max(memoryAfter - memoryBefore, 0) / BYTES_PER_MB;
        return new Measurement(name, elapsed, memoryMb, cpuPercent(cpuUsed, elapsed));
    }

    public static double throughput(int itemCount, Duration elapsed) {
        if (elapsed.toNanos() <= 0) {
            throw new IllegalArgumentException("elapsed time must be greater than zero");
        }
        if (itemCount < 0) {
            throw new IllegalArgumentException("item count cannot be negative");
        }
        return itemCount / (elapsed.toNanos() / 1_000_000_000.0);
    }

    static long rssBytes() {
        Path status = Path.of("/proc/self/status");
        if (!Files.isRegularFile(status)) {
            return 0;
        }
        try (Stream<String> lines = Files.lines(status, StandardCharsets.UTF_8)) {
            return lines.filter(line -> line.startsWith("VmRSS:"))
                .map(line -> line.replaceAll("[^0-9]", ""))
                .filter(digits -> !digits.isEmpty())
                .map(Long::parseLong)
                .findFirst()
                .orElse(0L) * 1024;
        } catch (IOException exception) {
            return 0;
        }
    }

    static long processCpuTimeNanos() {
        OperatingSystemMXBean system = (OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean();
        return system.getProcessCpuTime();
    }

    private static double cpuPercent(long cpuUsedNanos, Duration elapsed) {
        if (elapsed.toNanos() <= 0 || cpuUsedNanos < 0) {
            return 0;
        }
        return cpuUsedNanos / (double) elapsed.toNanos() * 100.0;
    }

    @FunctionalInterface
    public interface Operation {
        void run() throws IOException;
    }
}
