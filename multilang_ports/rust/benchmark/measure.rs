use super::BenchResult;
use std::fs;
use std::time::{Duration, Instant};

const BYTES_PER_MB: f64 = 1024.0 * 1024.0;
const NANOSECONDS_PER_CPU_TICK: f64 = 1_000_000_000.0 / 100.0;

#[derive(Debug)]
pub struct Measurement {
    pub name: String,
    pub elapsed: Duration,
    pub memory_mb: f64,
    pub cpu_percent: f64,
}

impl Measurement {
    pub fn seconds(&self) -> f64 {
        self.elapsed.as_secs_f64()
    }
}

pub fn measure<F>(name: &str, operation: F) -> BenchResult<Measurement>
where
    F: FnOnce() -> BenchResult<()>,
{
    let memory_before = rss_bytes();
    let cpu_before = process_cpu_time();
    let start = Instant::now();

    operation().map_err(|error| format!("{name}: {error}"))?;

    let elapsed = start.elapsed();
    let memory_after = rss_bytes();
    let cpu_used = process_cpu_time() - cpu_before;
    Ok(Measurement {
        name: name.to_string(),
        elapsed,
        memory_mb: (memory_after.saturating_sub(memory_before)) as f64 / BYTES_PER_MB,
        cpu_percent: cpu_percent(cpu_used, elapsed),
    })
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
}
