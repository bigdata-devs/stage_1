package benchmark;

import java.time.Duration;

public record Measurement(String name, Duration elapsed, double memoryMb, double cpuPercent) {

    public double seconds() {
        return elapsed.toNanos() / 1_000_000_000.0;
    }
}
