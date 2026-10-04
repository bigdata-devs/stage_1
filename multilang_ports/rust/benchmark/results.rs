use super::disk::DiskUsage;
use super::measure::Measurement;
use super::recovery::RecoveryReport;
use super::statistics::Statistics;
use super::BenchResult;
use chrono::Local;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Duration;

const TIMESTAMP_FORMAT: &str = "%Y-%m-%dT%H:%M:%S%.6f";

pub struct ResultsWriter {
    dir: PathBuf,
}

impl ResultsWriter {
    pub fn new(dir: &Path) -> Self {
        Self {
            dir: dir.to_path_buf(),
        }
    }

    pub fn save_measurement(&self, measurement: &Measurement) -> BenchResult<()> {
        self.append_timestamped_row(
            "benchmarks.csv",
            &["function_name", "elapsed_seconds", "memory_mb", "cpu_percent"],
            vec![
                measurement.name.clone(),
                format!("{:.6}", measurement.seconds()),
                format!("{:.4}", measurement.memory_mb),
                format!("{:.2}", measurement.cpu_percent),
            ],
        )
    }

    pub fn save_disk_usage(&self, usage: &DiskUsage) -> BenchResult<()> {
        self.append_timestamped_row(
            "disk_usage.csv",
            &["path", "size_mb", "file_count", "dir_count"],
            vec![
                usage.path.clone(),
                format!("{:.4}", usage.size_mb),
                usage.file_count.to_string(),
                usage.dir_count.to_string(),
            ],
        )
    }

    pub fn save_throughput(
        &self,
        test_name: &str,
        item_count: usize,
        elapsed: Duration,
        items_per_second: f64,
    ) -> BenchResult<()> {
        self.append_timestamped_row(
            "throughput.csv",
            &["test_name", "item_count", "elapsed_seconds", "items_per_second"],
            vec![
                test_name.to_string(),
                item_count.to_string(),
                format!("{:.6}", elapsed.as_secs_f64()),
                format!("{:.4}", items_per_second),
            ],
        )
    }

    pub fn save_statistics(&self, test_name: &str, statistics: &Statistics) -> BenchResult<()> {
        self.append_timestamped_row(
            "statistics.csv",
            &[
                "test_name",
                "iterations",
                "mean_seconds",
                "stdev_seconds",
                "min_seconds",
                "max_seconds",
            ],
            vec![
                test_name.to_string(),
                statistics.iterations.to_string(),
                format!("{:.6}", statistics.mean_seconds),
                format!("{:.6}", statistics.stdev_seconds),
                format!("{:.6}", statistics.min_seconds),
                format!("{:.6}", statistics.max_seconds),
            ],
        )
    }

    pub fn save_scalability(
        &self,
        test_name: &str,
        batch_size: usize,
        measurement: &Measurement,
    ) -> BenchResult<()> {
        self.append_timestamped_row(
            "scalability.csv",
            &[
                "test_name",
                "batch_size",
                "elapsed_seconds",
                "memory_mb",
                "cpu_percent",
            ],
            vec![
                test_name.to_string(),
                batch_size.to_string(),
                format!("{:.6}", measurement.seconds()),
                format!("{:.4}", measurement.memory_mb),
                format!("{:.2}", measurement.cpu_percent),
            ],
        )
    }

    pub fn save_recovery(&self, test_name: &str, report: &RecoveryReport) -> BenchResult<()> {
        self.append_timestamped_row(
            "recovery.csv",
            &[
                "test_name",
                "total_books",
                "processed_before_interruption",
                "processed_after_resume",
                "duplicated",
                "lost",
                "detection_time",
                "processing_time",
                "elapsed_seconds",
            ],
            vec![
                test_name.to_string(),
                report.total_books.to_string(),
                report.processed_before.to_string(),
                report.processed_after.to_string(),
                report.duplicated.to_string(),
                report.lost.to_string(),
                format!("{:.6}", report.detection_time.as_secs_f64()),
                format!("{:.6}", report.processing_time.as_secs_f64()),
                format!("{:.6}", report.elapsed.as_secs_f64()),
            ],
        )
    }

    fn append_timestamped_row(
        &self,
        file_name: &str,
        header: &[&str],
        row: Vec<String>,
    ) -> BenchResult<()> {
        fs::create_dir_all(&self.dir)?;
        let path = self.dir.join(file_name);
        let mut lines = String::new();
        if !path.exists() {
            let mut columns: Vec<String> = header.iter().map(|name| name.to_string()).collect();
            columns.push("timestamp".to_string());
            lines.push_str(&encode_line(&columns));
        }
        let mut columns = row;
        columns.push(Local::now().format(TIMESTAMP_FORMAT).to_string());
        lines.push_str(&encode_line(&columns));
        let mut file = OpenOptions::new().create(true).append(true).open(path)?;
        file.write_all(lines.as_bytes())?;
        Ok(())
    }
}

fn encode_line(values: &[String]) -> String {
    let mut line = String::new();
    for (position, value) in values.iter().enumerate() {
        if position > 0 {
            line.push(',');
        }
        line.push_str(&escape(value));
    }
    line.push_str("\r\n");
    line
}

fn escape(value: &str) -> String {
    if value.contains(',') || value.contains('"') || value.contains('\r') || value.contains('\n') {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_results_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        dir
    }

    fn measurement(name: &str, seconds: u64) -> Measurement {
        Measurement {
            name: name.to_string(),
            elapsed: Duration::from_secs(seconds),
            memory_mb: 12.5,
            cpu_percent: 33.333,
        }
    }

    #[test]
    fn measurement_row_uses_six_four_two_decimals_and_crlf() {
        let dir = temp_dir("measurement");
        let writer = ResultsWriter::new(&dir);
        writer.save_measurement(&measurement("tokenize_books", 2)).unwrap();
        let content = fs::read_to_string(dir.join("benchmarks.csv")).unwrap();
        let lines: Vec<&str> = content.split("\r\n").collect();
        assert_eq!(
            "function_name,elapsed_seconds,memory_mb,cpu_percent,timestamp",
            lines[0]
        );
        assert!(lines[1].starts_with("tokenize_books,2.000000,12.5000,33.33,"));
        assert_eq!(26, lines[1].split(',').last().unwrap().len());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn second_row_appends_without_header() {
        let dir = temp_dir("append");
        let writer = ResultsWriter::new(&dir);
        writer.save_measurement(&measurement("first", 1)).unwrap();
        writer.save_measurement(&measurement("second", 3)).unwrap();
        let content = fs::read_to_string(dir.join("benchmarks.csv")).unwrap();
        let lines: Vec<&str> = content.split("\r\n").collect();
        assert_eq!(4, lines.len());
        assert!(lines[3].is_empty());
        assert!(!lines[1].contains("function_name"));
        assert!(lines[2].starts_with("second,3.000000,"));
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn statistics_row_uses_six_decimals_for_every_value() {
        let dir = temp_dir("statistics");
        let writer = ResultsWriter::new(&dir);
        writer
            .save_statistics(
                "query_json_index",
                &Statistics {
                    iterations: 5,
                    mean_seconds: 0.001234,
                    stdev_seconds: 0.000567,
                    min_seconds: 0.000891,
                    max_seconds: 0.002345,
                },
            )
            .unwrap();
        let content = fs::read_to_string(dir.join("statistics.csv")).unwrap();
        assert!(content.contains("query_json_index,5,0.001234,0.000567,0.000891,0.002345,"));
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn disk_throughput_scalability_and_recovery_rows_match_column_order() {
        let dir = temp_dir("rows");
        let writer = ResultsWriter::new(&dir);
        writer
            .save_disk_usage(&DiskUsage {
                path: "/tmp/idx".to_string(),
                size_mb: 4.125,
                file_count: 12,
                dir_count: 3,
            })
            .unwrap();
        writer
            .save_throughput("write_throughput_book_based", 100, Duration::from_secs(5), 20.5)
            .unwrap();
        writer
            .save_scalability("build_json_index", 25, &measurement("build", 1))
            .unwrap();
        writer
            .save_recovery(
                "recovery_book_based",
                &RecoveryReport {
                    total_books: 100,
                    processed_before: 50,
                    processed_after: 50,
                    duplicated: 0,
                    lost: 0,
                    detection_time: Duration::from_millis(5),
                    processing_time: Duration::from_millis(7),
                    elapsed: Duration::from_millis(12),
                },
            )
            .unwrap();
        let disk = fs::read_to_string(dir.join("disk_usage.csv")).unwrap();
        assert!(disk.contains("/tmp/idx,4.1250,12,3,"));
        let throughput = fs::read_to_string(dir.join("throughput.csv")).unwrap();
        assert!(throughput.contains("write_throughput_book_based,100,5.000000,20.5000,"));
        let scalability = fs::read_to_string(dir.join("scalability.csv")).unwrap();
        assert!(scalability.contains("build_json_index,25,1.000000,12.5000,33.33,"));
        let recovery = fs::read_to_string(dir.join("recovery.csv")).unwrap();
        assert!(recovery.contains("recovery_book_based,100,50,50,0,0,0.005000,0.007000,0.012000,"));
        fs::remove_dir_all(&dir).unwrap();
    }
}
