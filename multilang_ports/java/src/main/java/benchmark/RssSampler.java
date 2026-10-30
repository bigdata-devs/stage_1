package benchmark;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Samples the resident set size of this process every 50 ms while an
 * operation runs, so the benchmark can report the absolute memory footprint
 * (peak RSS) and not only the growth around the operation.
 */
final class RssSampler {

    private static final long SAMPLE_INTERVAL_MILLIS = 50;

    private final AtomicLong peakBytes;
    private final Thread samplingThread;

    private RssSampler(long initialBytes) {
        this.peakBytes = new AtomicLong(initialBytes);
        this.samplingThread = new Thread(this::sampleUntilInterrupted, "rss-sampler");
    }

    static RssSampler start(long initialBytes) {
        RssSampler sampler = new RssSampler(initialBytes);
        sampler.samplingThread.start();
        return sampler;
    }

    /** Stops the sampling thread and reports the largest value seen, finalBytes included. */
    long stop(long finalBytes) {
        samplingThread.interrupt();
        awaitSamplingThread();
        peakBytes.accumulateAndGet(finalBytes, Math::max);
        return peakBytes.get();
    }

    private void sampleUntilInterrupted() {
        while (!Thread.currentThread().isInterrupted()) {
            peakBytes.accumulateAndGet(Measure.rssBytes(), Math::max);
            try {
                Thread.sleep(SAMPLE_INTERVAL_MILLIS);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
            }
        }
    }

    private void awaitSamplingThread() {
        try {
            samplingThread.join();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
        }
    }
}
