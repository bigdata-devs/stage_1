package benchmark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;

class BuildAggregateTest {

    @Test
    void averagesSamplesAndKeepsTheLargestPeak() {
        List<Measurement> samples = List.of(
            new Measurement("build", Duration.ofSeconds(1), 2.0, 10.0, 40.0),
            new Measurement("build", Duration.ofSeconds(3), 4.0, 30.0, 60.0));

        BuildAggregate aggregate = BuildAggregate.of(samples);

        assertEquals(2, aggregate.repetitions());
        assertEquals(2.0, aggregate.elapsedSeconds(), 1e-9);
        assertEquals(Math.sqrt(2), aggregate.stdevSeconds(), 1e-9);
        assertEquals(3.0, aggregate.memoryMb(), 1e-9);
        assertEquals(50.0, aggregate.cpuPercent(), 1e-9);
        assertEquals(30.0, aggregate.peakRssMb(), 1e-9);
    }

    @Test
    void singleSampleHasZeroStdev() {
        BuildAggregate aggregate = BuildAggregate.of(List.of(new Measurement("build", Duration.ofMillis(500), 1.0, 1.0, 1.0)));

        assertEquals(0.0, aggregate.stdevSeconds(), 1e-9);
    }

    @Test
    void emptySamplesAreRejected() {
        assertThrows(IllegalArgumentException.class, () -> BuildAggregate.of(List.of()));
    }
}
