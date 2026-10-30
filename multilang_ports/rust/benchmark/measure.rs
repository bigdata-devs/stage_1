use super::statistics::{mean, sample_stdev};
use super::BenchResult;
use std::fs;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc;
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

const BYTES_PER_MB: f64 = 1024.0 * 1024.0;
const NANOSECONDS_PER_CPU_TICK: f64 = 1_000_000_000.0 / 100.0;
const RSS_SAMPLE_INTERVAL: Duration = Duration::from_millis(50);

#[derive(Debug)]
pub struct Measurement {
    pub name: String,
    pub elapsed: Duration,
    pub memory_mb: f64,
    pub peak_rss_mb: f64,
    pub cpu_percent: f64,
}

impl Measurement {
    pub fn seconds(&self) -> f64 {
        self.elapsed.as_secs_f64()
    }
}

/// The repeated measurements of one scalability batch, mirroring the fields
/// that save_scalability() stores in the other language ports.
#[derive(Debug)]
pub struct BuildAggregate {
    pub elapsed_seconds: f64,
    pub stdev_seconds: f64,
    pub repetitions: usize,
    pub memory_mb: f64,
    pub cpu_percent: f64,
    pub peak_rss_mb: f64,
}

/// Reduces the samples of one batch to their mean behaviour: elapsed, memory
/// and CPU are averaged, the peak RSS is the largest sample.
pub fn aggregate_build(measurements: &[Measurement]) -> BenchResult<BuildAggregate> {
    if measurements.is_empty() {
        return Err("measurements must not be empty".into());
    }
    let elapsed: Vec<f64> = measurements.iter().map(Measurement::seconds).collect();
    let mean_elapsed = mean(&elapsed);
    Ok(BuildAggregate {
        elapsed_seconds: mean_elapsed,
        stdev_seconds: sample_stdev(&elapsed, mean_elapsed),
        repetitions: measurements.len(),
        memory_mb: mean_resource(measurements, |measurement| measurement.memory_mb),
        cpu_percent: mean_resource(measurements, |measurement| measurement.cpu_percent),
        peak_rss_mb: measurements
            .iter()
            .map(|measurement| measurement.peak_rss_mb)
            .fold(0.0, f64::max),
    })
}

fn mean_resource(measurements: &[Measurement], value: impl Fn(&Measurement) -> f64) -> f64 {
    let total: f64 = measurements.iter().map(&value).sum();
    total / measurements.len() as f64
}

pub fn measure<F>(name: &str, operation: F) -> BenchResult<Measurement>
where
    F: FnOnce() -> BenchResult<()>,
{
    let memory_before = rss_bytes();
    let peak_sampler = PeakRssSampler::start(memory_before);
    let cpu_before = process_cpu_time();
    let start = Instant::now();

    let operation_result = operation();

    let elapsed = start.elapsed();
    let memory_after = rss_bytes();
    let peak_rss_bytes = peak_sampler.stop(memory_after);
    let cpu_used = process_cpu_time() - cpu_before;
    operation_result.map_err(|error| format!("{name}: {error}"))?;
    Ok(Measurement {
        name: name.to_string(),
        elapsed,
        memory_mb: (memory_after.saturating_sub(memory_before)) as f64 / BYTES_PER_MB,
        peak_rss_mb: peak_rss_bytes as f64 / BYTES_PER_MB,
        cpu_percent: cpu_percent(cpu_used, elapsed),
    })
}

/// Samples the resident set size of this process while an operation runs.
struct PeakRssSampler {
    peak_bytes: Arc<AtomicU64>,
    stop_signal: mpsc::Sender<()>,
    sampling_thread: thread::JoinHandle<()>,
}

impl PeakRssSampler {
    fn start(initial_bytes: u64) -> Self {
        let peak_bytes = Arc::new(AtomicU64::new(initial_bytes));
        let (stop_signal, stop_receiver) = mpsc::channel();
        let sampling_thread = {
            let peak_bytes = Arc::clone(&peak_bytes);
            thread::spawn(move || {
                while stop_receiver.recv_timeout(RSS_SAMPLE_INTERVAL).is_err() {
                    store_max(&peak_bytes, rss_bytes());
                }
            })
        };
        Self {
            peak_bytes,
            stop_signal,
            sampling_thread,
        }
    }

    /// Stops the sampling thread and reports the largest value seen,
    /// including final_bytes.
    fn stop(self, final_bytes: u64) -> u64 {
        let _ = self.stop_signal.send(());
        let _ = self.sampling_thread.join();
        store_max(&self.peak_bytes, final_bytes);
        self.peak_bytes.load(Ordering::Relaxed)
    }
}

fn store_max(value: &AtomicU64, sample: u64) {
    let mut current = value.load(Ordering::Relaxed);
    while sample > current {
        match value.compare_exchange_weak(current, sample, Ordering::Relaxed, Ordering::Relaxed) {
            Ok(_) => return,
            Err(updated) => current = updated,
        }
    }
}

pub fn throughput(item_count: usize, elapsed: Duration) -> BenchResult<f64> {
    if elapsed.as_secs_f64() <= 0.0 {
        return Err("elapsed time must be greater than zero".into());
    }
    Ok(item_count as f64 / elapsed.as_secs_f64())
}

fn cpu_percent(cpu_used: f64, elapsed: Duration) -> f64 {
    if elapsed.as_nanos() == 0 {
        return 0.0;
    }
    cpu_used / elapsed.as_nanos() as f64 * 100.0
}

fn rss_bytes() -> u64 {
    let Ok(status) = fs::read_to_string("/proc/self/status") else {
        return 0;
    };
    status
        .lines()
        .find(|line| line.starts_with("VmRSS:"))
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|kilobytes| kilobytes.parse::<u64>().ok())
        .map(|kilobytes| kilobytes * 1024)
        .unwrap_or(0)
}

fn process_cpu_time() -> f64 {
    let Ok(stat) = fs::read_to_string("/proc/self/stat") else {
        return 0.0;
    };
    let Some((_, after_command)) = stat.rsplit_once(')') else {
        return 0.0;
    };
    let fields: Vec<&str> = after_command.split_whitespace().collect();
    // After the closing parenthesis the fields start at "state" (field 3),
    // so utime (14) and stime (15) sit at indexes 11 and 12.
    let utime: f64 = fields.get(11).and_then(|value| value.parse().ok()).unwrap_or(0.0);
    let stime: f64 = fields.get(12).and_then(|value| value.parse().ok()).unwrap_or(0.0);
    (utime + stime) * NANOSECONDS_PER_CPU_TICK
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn measure_captures_elapsed_time_and_non_negative_resources() {
        let measurement = measure("demo", || Ok(())).unwrap();
        assert_eq!("demo", measurement.name);
        assert!(measurement.seconds() >= 0.0);
        assert!(measurement.memory_mb >= 0.0);
        assert!(measurement.cpu_percent >= 0.0);
    }

    #[test]
    fn failing_operation_propagates_the_error_with_the_measurement_name() {
        let error = measure("failing", || Err("boom".into())).unwrap_err();
        assert!(error.to_string().contains("failing"));
        assert!(error.to_string().contains("boom"));
    }

    #[test]
    fn throughput_divides_item_count_by_elapsed_time() {
        assert_eq!(5.0, throughput(10, Duration::from_secs(2)).unwrap());
        assert_eq!(0.0, throughput(0, Duration::from_secs(1)).unwrap());
        assert!(throughput(1, Duration::ZERO).is_err());
    }

    #[test]
    fn rss_bytes_is_readable_from_proc() {
        assert!(rss_bytes() > 0 || !std::path::Path::new("/proc/self/status").exists());
    }

    #[test]
    fn aggregate_build_averages_samples_and_keeps_the_largest_peak() {
        let measurements = vec![
            Measurement {
                name: "build".to_string(),
                elapsed: Duration::from_secs(1),
                memory_mb: 2.0,
                peak_rss_mb: 10.0,
                cpu_percent: 40.0,
            },
            Measurement {
                name: "build".to_string(),
                elapsed: Duration::from_secs(3),
                memory_mb: 4.0,
                peak_rss_mb: 30.0,
                cpu_percent: 60.0,
            },
        ];
        let aggregate = aggregate_build(&measurements).unwrap();
        assert_eq!(2, aggregate.repetitions);
        assert_eq!(2.0, aggregate.elapsed_seconds);
        assert!((aggregate.stdev_seconds - 2.0_f64.sqrt()).abs() < 1e-9);
        assert_eq!(3.0, aggregate.memory_mb);
        assert_eq!(50.0, aggregate.cpu_percent);
        assert_eq!(30.0, aggregate.peak_rss_mb);
    }

    #[test]
    fn aggregate_build_rejects_empty_samples() {
        assert!(aggregate_build(&[]).is_err());
    }
}
