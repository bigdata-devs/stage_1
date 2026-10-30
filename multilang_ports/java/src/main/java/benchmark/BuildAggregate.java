package benchmark;

import java.util.List;
import java.util.function.ToDoubleFunction;

/**
 * The repeated measurements of one scalability batch, mirroring the fields
 * that save_scalability() stores in the other language ports: elapsed, memory
 * and CPU are averaged, the peak RSS is the largest sample.
 */
public record BuildAggregate(double elapsedSeconds, double stdevSeconds, int repetitions,
        double memoryMb, double cpuPercent, double peakRssMb) {

    public static BuildAggregate of(List<Measurement> samples) {
        if (samples.isEmpty()) {
            throw new IllegalArgumentException("samples must not be empty");
        }
        double meanElapsed = meanOf(samples, Measurement::seconds);
        return new BuildAggregate(meanElapsed, sampleStandardDeviation(samples, meanElapsed), samples.size(),
            meanOf(samples, Measurement::memoryMb), meanOf(samples, Measurement::cpuPercent),
            samples.stream().mapToDouble(Measurement::peakRssMb).max().orElse(0));
    }

    private static double meanOf(List<Measurement> samples, ToDoubleFunction<Measurement> value) {
        return samples.stream().mapToDouble(value).average().orElse(0);
    }

    private static double sampleStandardDeviation(List<Measurement> samples, double mean) {
        if (samples.size() < 2) {
            return 0;
        }
        double squaredDeviations = 0;
        for (Measurement sample : samples) {
            double deviation = sample.seconds() - mean;
            squaredDeviations += deviation * deviation;
        }
        return Math.sqrt(squaredDeviations / (samples.size() - 1));
    }
}
