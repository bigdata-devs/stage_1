use super::queries;
use super::BenchResult;
use crate::inverted_index::corpus;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

pub const DEFAULT_BODIES_DIR: &str = "../../data_source/bodies";
pub const DEFAULT_HEADERS_DIR: &str = "../../data_source/headers";
pub const DEFAULT_QUERIES_PATH: &str = "../../src/utils/benchmarks/queries.txt";
pub const DEFAULT_GUTENBERG_URL: &str = "https://www.gutenberg.org/cache/epub";
pub const DEFAULT_MONGO_URI: &str = "mongodb://localhost:27017";
pub const DEFAULT_MONGO_DATABASE: &str = "search_engine";
pub const DEFAULT_MONGO_COLLECTION: &str = "inverted_index";

const BOOLEAN_FLAGS: [&str; 3] = ["-skip-datalake", "-skip-index", "-skip-mongo"];

pub struct Config {
    pub book_ids: Vec<i32>,
    pub raw_books_dir: String,
    pub gutenberg_url: String,
    pub bodies_dir: PathBuf,
    pub headers_dir: PathBuf,
    pub output_dir: PathBuf,
    pub results_dir: PathBuf,
    pub mongo_uri: String,
    pub mongo_database: String,
    pub mongo_collection: String,
    pub queries: Vec<Vec<String>>,
    pub query_repetitions: usize,
    pub skip_datalake: bool,
    pub skip_index: bool,
    pub skip_mongo: bool,
}

impl Config {
    pub fn parse(args: &[String]) -> BenchResult<Self> {
        let flags = parse_flags(args)?;
        let query_repetitions = flags
            .get("-query-repetitions")
            .map(|value| value.parse::<usize>())
            .transpose()
            .map_err(|_| "-query-repetitions must be a number")?
            .unwrap_or(5);
        if query_repetitions < 1 {
            return Err("-query-repetitions must be at least 1".into());
        }
        let bodies_dir = PathBuf::from(
            flags
                .get("-bodies")
                .map_or(DEFAULT_BODIES_DIR, String::as_str),
        );
        let queries = queries::load(Path::new(
            flags
                .get("-queries")
                .map_or(DEFAULT_QUERIES_PATH, String::as_str),
        ))?;
        let book_ids = match flags.get("-ids") {
            Some(value) => parse_book_ids(value)?,
            None => corpus::discover_book_ids(&bodies_dir)?,
        };
        Ok(Self {
            book_ids,
            raw_books_dir: flags.get("-raw-dir").cloned().unwrap_or_default(),
            gutenberg_url: flags
                .get("-gutenberg-url")
                .cloned()
                .unwrap_or_else(|| DEFAULT_GUTENBERG_URL.to_string()),
            bodies_dir,
            headers_dir: PathBuf::from(
                flags
                    .get("-headers")
                    .map_or(DEFAULT_HEADERS_DIR, String::as_str),
            ),
            output_dir: PathBuf::from(
                flags.get("-out").cloned().unwrap_or_else(default_artifact_dir),
            ),
            results_dir: PathBuf::from(
                flags.get("-results").cloned().unwrap_or_else(|| "results".to_string()),
            ),
            mongo_uri: flags
                .get("-mongo-uri")
                .cloned()
                .unwrap_or_else(|| DEFAULT_MONGO_URI.to_string()),
            mongo_database: flags
                .get("-mongo-db")
                .cloned()
                .unwrap_or_else(|| DEFAULT_MONGO_DATABASE.to_string()),
            mongo_collection: flags
                .get("-mongo-collection")
                .cloned()
                .unwrap_or_else(|| DEFAULT_MONGO_COLLECTION.to_string()),
            queries,
            query_repetitions,
            skip_datalake: flags.contains_key("-skip-datalake"),
            skip_index: flags.contains_key("-skip-index"),
            skip_mongo: flags.contains_key("-skip-mongo"),
        })
    }
}

fn parse_flags(args: &[String]) -> BenchResult<HashMap<String, String>> {
    let mut flags = HashMap::new();
    let mut position = 0;
    while position < args.len() {
        let argument = &args[position];
        let (name, value) = match argument.split_once('=') {
            Some((name, value)) => (name.to_string(), Some(value.to_string())),
            None => (argument.clone(), None),
        };
        let value = match value {
            Some(value) => value,
            None if BOOLEAN_FLAGS.contains(&name.as_str()) => String::new(),
            None => {
                position += 1;
                let Some(next) = args.get(position) else {
                    return Err(format!("missing value for {name}").into());
                };
                next.clone()
            }
        };
        flags.insert(name, value);
        position += 1;
    }
    Ok(flags)
}

fn parse_book_ids(value: &str) -> BenchResult<Vec<i32>> {
    let mut book_ids = Vec::new();
    for item in value.split(',') {
        let trimmed = item.trim();
        if !trimmed.is_empty() {
            book_ids.push(trimmed.parse().map_err(|_| format!("invalid book id {trimmed}"))?);
        }
    }
    Ok(book_ids)
}

fn default_artifact_dir() -> String {
    std::env::var("HOME")
        .map(|home| {
            Path::new(&home)
                .join(".cache")
                .join("stage_1_benchmarks")
                .join("rust")
                .to_string_lossy()
                .into_owned()
        })
        .unwrap_or_else(|_| "output".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_dir(label: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "stage1_rust_config_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn workload_file(dir: &Path) -> PathBuf {
        let path = dir.join("queries.txt");
        fs::write(&path, "alpha beta\n").unwrap();
        path
    }

    #[test]
    fn parse_reads_explicit_flags() {
        let dir = temp_dir("explicit");
        let args: Vec<String> = [
            "-ids".to_string(),
            "5, 1,3".to_string(),
            "-bodies".to_string(),
            dir.join("bodies").to_string_lossy().into_owned(),
            "-queries".to_string(),
            workload_file(&dir).to_string_lossy().into_owned(),
            "-results".to_string(),
            dir.join("results").to_string_lossy().into_owned(),
            "-query-repetitions".to_string(),
            "7".to_string(),
            "-skip-mongo".to_string(),
        ]
        .to_vec();
        let config = Config::parse(&args).unwrap();
        assert_eq!(vec![5, 1, 3], config.book_ids);
        assert_eq!(7, config.query_repetitions);
        assert!(config.skip_mongo);
        assert!(!config.skip_datalake);
        assert_eq!(1, config.queries.len());
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn missing_ids_flag_discovers_the_corpus_bodies() {
        let dir = temp_dir("discover");
        let bodies = dir.join("bodies");
        fs::create_dir_all(&bodies).unwrap();
        fs::write(bodies.join("84_body.txt"), "text").unwrap();
        fs::write(bodies.join("11_body.txt"), "text").unwrap();
        let args = vec![
            "-bodies".to_string(),
            bodies.to_string_lossy().into_owned(),
            "-queries".to_string(),
            workload_file(&dir).to_string_lossy().into_owned(),
        ];
        let config = Config::parse(&args).unwrap();
        assert_eq!(vec![11, 84], config.book_ids);
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn zero_repetitions_and_missing_flag_values_are_rejected() {
        let dir = temp_dir("invalid");
        let queries = workload_file(&dir);
        let zero = vec![
            "-queries".to_string(),
            queries.to_string_lossy().into_owned(),
            "-query-repetitions".to_string(),
            "0".to_string(),
        ];
        assert!(Config::parse(&zero).is_err());
        let missing = vec!["-bodies".to_string()];
        assert!(Config::parse(&missing).is_err());
        fs::remove_dir_all(&dir).unwrap();
    }
}
