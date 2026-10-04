package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;

class MeasureTest {

    @Test
    void measureCapturesElapsedTimeAndNonNegativeResources() throws IOException {
        Measurement measurement = Measure.measure("demo", () -> {
            AtomicBoolean ran = new AtomicBoolean(false);
            ran.set(true);
        });

        assertEquals("demo", measurement.name());
        assertTrue(measurement.seconds() >= 0);
        assertTrue(measurement.memoryMb() >= 0);
        assertTrue(measurement.cpuPercent() >= 0);
    }

    @Test
    void failingOperationPropagatesTheIOException() {
        assertThrows(IOException.class,
            () -> Measure.measure("failing", () -> {
                throw new IOException("boom");
            }));
    }

    @Test
    void throughputDividesItemCountByElapsedTime() {
        assertEquals(5.0, Measure.throughput(10, Duration.ofSeconds(2)), 1e-9);
        assertEquals(0.0, Measure.throughput(0, Duration.ofSeconds(1)), 1e-9);
        assertThrows(IllegalArgumentException.class, () -> Measure.throughput(1, Duration.ZERO));
        assertThrows(IllegalArgumentException.class, () -> Measure.throughput(-1, Duration.ofSeconds(1)));
    }

    @Test
    void rssBytesIsReadableFromProc() {
        assertTrue(Measure.rssBytes() >= 0);
    }
}
