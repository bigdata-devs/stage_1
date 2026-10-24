package benchmark;

import java.time.Duration;

public record RecoveryReport(int totalBooks, int processedBefore, int processedAfter,
        int duplicated, int lost, Duration detectionTime, Duration processingTime, Duration elapsed) {
}
