use super::measure;
use super::suite::{first_ids, reset_directory, Suite};
use super::BenchResult;
use crate::datalake::layout::{read_book_body, read_book_header, Layout};
use crate::datalake::store::{pending_book_ids, Datalake};
use crate::datalake::time_based::TimeBased;
use std::path::Path;
use std::time::Instant;

const DOWNLOAD_PROBE_COUNT: usize = 10;

pub fn run(suite: &Suite) -> BenchResult<()> {
    for layout in super::suite::layouts() {
        benchmark_layout(suite, layout.as_ref())?;
    }
    measure_download_probe(suite)
}

fn benchmark_layout(suite: &Suite, layout: &dyn Layout) -> BenchResult<()> {
    let root = suite.output_path(&["datalake", layout.name()]);
    reset_directory(&root)?;
    measure_layout_write(suite, layout, &root)?;
    measure_layout_lookup(suite, layout, &root)?;
    measure_layout_incremental(suite, layout, &root)?;
    measure_layout_recovery(suite, layout, &root)?;
    suite.record_disk_usage(&root)
}

fn measure_layout_write(suite: &Suite, layout: &dyn Layout, root: &Path) -> BenchResult<()> {
    let measurement = suite.measure(&format!("write_throughput_{}", layout.name()), || {
        populate_from_corpus(suite, layout, root)
    })?;
    suite.record_throughput(&measurement, suite.config().book_ids.len())
}

fn populate_from_corpus(suite: &Suite, layout: &dyn Layout, root: &Path) -> BenchResult<()> {
    let config = suite.config();
    let lake = Datalake::new(root, layout);
    for &book_id in &config.book_ids {
        let body = read_book_body(book_id, &config.bodies_dir)?;
        let header = read_book_header(book_id, &config.headers_dir)?;
        lake.store(book_id, &header, &body)?;
    }
    Ok(())
}

fn measure_layout_lookup(suite: &Suite, layout: &dyn Layout, root: &Path) -> BenchResult<()> {
    let mut durations = Vec::with_capacity(suite.config().book_ids.len());
    for &book_id in &suite.config().book_ids {
        let start = Instant::now();
        layout.locate(root, book_id)?;
        durations.push(start.elapsed());
    }
    suite.record_query_statistics(&format!("lookup_{}", layout.name()), &durations)
}

fn measure_layout_incremental(suite: &Suite, layout: &dyn Layout, root: &Path) -> BenchResult<()> {
    let known = first_ids(&suite.config().book_ids, suite.config().book_ids.len() / 2);
    suite.measure(&format!("incremental_{}", layout.name()), || {
        pending_book_ids(root, &known)?;
        Ok(())
    })?;
    Ok(())
}

fn measure_layout_recovery(suite: &Suite, layout: &dyn Layout, root: &Path) -> BenchResult<()> {
    let report =
        super::recovery::resume_after_interruption(layout, root, &suite.config().book_ids)?;
    super::log::line(&format!(
        "[recovery_{}] {} resumed, {} duplicated, {} lost",
        layout.name(),
        report.processed_after,
        report.duplicated,
        report.lost
    ));
    suite.results().save_recovery(&format!("recovery_{}", layout.name()), &report)
}

fn measure_download_probe(suite: &Suite) -> BenchResult<()> {
    let probe_ids = first_ids(&suite.config().book_ids, DOWNLOAD_PROBE_COUNT);
    if probe_ids.is_empty() {
        return Ok(());
    }
    let probe_root = suite.output_path(&["datalake", "download_probe"]);
    reset_directory(&probe_root)?;
    let fetcher = suite.fetcher();
    let mut stored = 0usize;
    let measurement = measure::measure("download_write_throughput", || {
        stored = download_probe(fetcher.as_ref(), &probe_ids, &probe_root);
        Ok(())
    })?;
    if stored == 0 {
        super::log::line("[datalake] SKIP download_write_throughput: network unavailable");
        return Ok(());
    }
    suite.save_measurement(&measurement)?;
    suite.record_throughput(&measurement, stored)
}

fn download_probe(fetcher: &dyn crate::datalake::fetcher::Fetcher, probe_ids: &[i32], probe_root: &Path) -> usize {
    let lake = Datalake::new(probe_root, &TimeBased);
    probe_ids
        .iter()
        .filter(|&&book_id| lake.download(fetcher, book_id))
        .count()
}
