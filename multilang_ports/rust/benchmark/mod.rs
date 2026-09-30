mod config;
mod datalake_bench;
mod disk;
mod index_bench;
mod log;
mod measure;
mod queries;
mod recovery;
mod results;
mod statistics;
mod suite;

pub use config::Config;
pub use suite::Suite;

use std::error::Error;

pub type BenchResult<T> = Result<T, Box<dyn Error>>;
