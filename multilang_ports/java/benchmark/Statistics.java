package benchmark;

import java.time.Duration;
import java.util.List;

public record Statistics(int iterations, double meanSeconds, double stdevSeconds,
        double minSeconds, double maxSeconds) {

    public static Statistics calculate(List<Duration> durations) {
        if (durations.isEmpty()) {
            throw new IllegalArgumentException("durations must not be empty");
        }
        double min = Double.MAX_VALUE;
        double max = -Double.MAX_VALUE;
        double sum = 0;
        for (Duration duration : durations) {
            double seconds = duration.toNanos() / 1_000_000_000.0;
            min = Math.min(min, seconds);
            max = Math.max(max, seconds);
            sum += seconds;
        }
        double mean = sum / durations.size();
        return new Statistics(durations.size(), mean, sampleStandardDeviation(durations, mean), min, max);
    }

    private static double sampleStandardDeviation(List<Duration> durations, double mean) {
        if (durations.size() < 2) {
            return 0;
        }
        double squaredDeviations = 0;
        for (Duration duration : durations) {
            double deviation = duration.toNanos() / 1_000_000_000.0 - mean;
            squaredDeviations += deviation * deviation;
        }
        return Math.sqrt(squaredDeviations / (durations.size() - 1));
    }
}
