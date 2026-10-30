use super::BenchResult;
use std::time::Duration;

pub struct Statistics {
    pub iterations: usize,
    pub mean_seconds: f64,
    pub stdev_seconds: f64,
    pub min_seconds: f64,
    pub max_seconds: f64,
}

impl Statistics {
    pub fn calculate(durations: &[Duration]) -> BenchResult<Self> {
        if durations.is_empty() {
            return Err("durations must not be empty".into());
        }
        let seconds: Vec<f64> = durations.iter().map(Duration::as_secs_f64).collect();
        let mean = mean(&seconds);
        Ok(Self {
            iterations: seconds.len(),
            mean_seconds: mean,
            stdev_seconds: sample_stdev(&seconds, mean),
            min_seconds: seconds.iter().copied().fold(f64::MAX, f64::min),
            max_seconds: seconds.iter().copied().fold(f64::MIN, f64::max),
        })
    }
}

pub(crate) fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

pub(crate) fn sample_stdev(values: &[f64], mean: f64) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let squared_deviations: f64 = values
        .iter()
        .map(|value| {
            let deviation = value - mean;
            deviation * deviation
        })
        .sum();
    (squared_deviations / (values.len() - 1) as f64).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn calculate_returns_mean_stdev_min_and_max_in_seconds() {
        let statistics = Statistics::calculate(&[
            Duration::from_secs(1),
            Duration::from_secs(2),
            Duration::from_secs(3),
        ])
        .unwrap();
        assert_eq!(3, statistics.iterations);
        assert_eq!(2.0, statistics.mean_seconds);
        assert_eq!(1.0, statistics.stdev_seconds);
        assert_eq!(1.0, statistics.min_seconds);
        assert_eq!(3.0, statistics.max_seconds);
    }

    #[test]
    fn single_sample_has_zero_stdev() {
        let statistics = Statistics::calculate(&[Duration::from_millis(500)]).unwrap();
        assert_eq!(1, statistics.iterations);
        assert_eq!(0.0, statistics.stdev_seconds);
    }

    #[test]
    fn empty_durations_are_rejected() {
        assert!(Statistics::calculate(&[]).is_err());
    }
}
