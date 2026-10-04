package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;

class StatisticsTest {

    @Test
    void calculateReturnsMeanStdevMinAndMaxInSeconds() {
        Statistics statistics = Statistics.calculate(
            List.of(Duration.ofSeconds(1), Duration.ofSeconds(2), Duration.ofSeconds(3)));

        assertEquals(3, statistics.iterations());
        assertEquals(2.0, statistics.meanSeconds(), 1e-9);
        assertEquals(1.0, statistics.stdevSeconds(), 1e-9);
        assertEquals(1.0, statistics.minSeconds(), 1e-9);
        assertEquals(3.0, statistics.maxSeconds(), 1e-9);
    }

    @Test
    void singleSampleHasZeroStdev() {
        Statistics statistics = Statistics.calculate(List.of(Duration.ofMillis(500)));

        assertEquals(1, statistics.iterations());
        assertEquals(0.0, statistics.stdevSeconds(), 1e-9);
    }

    @Test
    void emptyDurationsAreRejected() {
        assertThrows(IllegalArgumentException.class, () -> Statistics.calculate(List.of()));
    }
}
