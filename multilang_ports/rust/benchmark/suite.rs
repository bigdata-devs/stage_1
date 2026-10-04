use super::config::Config;
use super::disk::DiskUsage;
use super::log;
use super::measure::{self, Measurement};
use super::results::ResultsWriter;
use super::statistics::Statistics;
use super::BenchResult;
use crate::datalake::fetcher::{DirectoryFetcher, Fetcher, GutenbergFetcher};
use crate::datalake::layout::Layout;
use crate::datalake::standard_layouts;
use crate::datamarts::mongo_index::{MongoIndex, MongoResult};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Duration;

pub struct Suite {
    config: Config,
    results: ResultsWriter,
}

impl Suite {
    pub fn new(config: Config) -> Self {
        let results = ResultsWriter::new(&config.results_dir);
        Self { config, results }
    }

    pub fn config(&self) -> &Config {
        &self.config
    }

    pub fn results(&self) -> &ResultsWriter {
        &self.results
    }

    pub fn run(&self) -> BenchResult<()> {
        if !self.config.skip_datalake {
            super::datalake_bench::run(self).map_err(|error| format!("datalake benchmark: {error}"))?;
        }
        if !self.config.skip_index {
            super::index_bench::run(self).map_err(|error| format!("index benchmark: {error}"))?;
        }
        log::line(&format!(
            "Results appended to {}",
            self.config.results_dir.display()
        ));
        Ok(())
    }

    pub fn measure<F>(&self, name: &str, operation: F) -> BenchResult<Measurement>
    where
        F: FnOnce() -> BenchResult<()>,
    {
        let measurement = measure::measure(name, operation)?;
        self.save_measurement(&measurement)?;
        Ok(measurement)
    }

    pub fn save_measurement(&self, measurement: &Measurement) -> BenchResult<()> {
        log::line(&format!(
            "[{}] {:.4}s | mem {:.2} MB | cpu {:.1}%",
            measurement.name,
            measurement.seconds(),
            measurement.memory_mb,
            measurement.cpu_percent
        ));
        self.results.save_measurement(measurement)
    }

    pub fn record_throughput(&self, measurement: &Measurement, item_count: usize) -> BenchResult<()> {
        let items_per_second = measure::throughput(item_count, measurement.elapsed)?;
        log::line(&format!(
            "[{}] throughput {:.4} items/s",
            measurement.name, items_per_second
        ));
        self.results.save_throughput(
            &measurement.name,
            item_count,
            measurement.elapsed,
            items_per_second,
        )
    }

    pub fn record_disk_usage(&self, path: &Path) -> BenchResult<()> {
        let usage = DiskUsage::measure(path)?;
        log::line(&format!(
            "[disk] {}: {:.4} MB, {} files, {} dirs",
            usage.path, usage.size_mb, usage.file_count, usage.dir_count
        ));
        self.results.save_disk_usage(&usage)
    }

    pub fn record_query_statistics(
        &self,
        test_name: &str,
        durations: &[Duration],
    ) -> BenchResult<()> {
        let statistics = Statistics::calculate(durations)?;
        log::line(&format!(
            "[{}] {} samples, mean {:.3} us, stdev {:.3} us",
            test_name,
            statistics.iterations,
            statistics.mean_seconds * 1_000_000.0,
            statistics.stdev_seconds * 1_000_000.0
        ));
        self.results.save_statistics(test_name, &statistics)
    }

    pub fn output_path(&self, parts: &[&str]) -> PathBuf {
        let mut output = self.config.output_dir.clone();
        for part in parts {
            output = output.join(part);
        }
        output
    }

    pub fn fetcher(&self) -> Box<dyn Fetcher> {
        if self.config.raw_books_dir.is_empty() {
            Box::new(GutenbergFetcher::with_base_url(&self.config.gutenberg_url))
        } else {
            Box::new(DirectoryFetcher::new(&self.config.raw_books_dir))
        }
    }

    pub fn connect_mongo(&self) -> MongoResult<MongoIndex> {
        MongoIndex::connect(
            &self.config.mongo_uri,
            &self.config.mongo_database,
            &self.config.mongo_collection,
        )
    }
}

pub fn first_ids(ids: &[i32], count: usize) -> Vec<i32> {
    if count >= ids.len() {
        return ids.to_vec();
    }
    ids[..count].to_vec()
}

pub fn reset_directory(path: &Path) -> BenchResult<()> {
    if path.is_dir() {
        fs::remove_dir_all(path)?;
    } else if path.exists() {
        fs::remove_file(path)?;
    }
    Ok(())
}

pub fn layouts() -> Vec<Box<dyn Layout>> {
    standard_layouts()
}
