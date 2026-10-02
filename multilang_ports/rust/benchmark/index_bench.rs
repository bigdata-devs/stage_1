use super::disk::DiskUsage;
use super::log;
use super::measure;
use super::queries;
use super::suite::Suite;
use super::BenchResult;
use crate::datamarts::folder_index;
use crate::datamarts::mongo_index::MongoIndex;
use crate::inverted_index::corpus;
use crate::inverted_index::json_index::{self, InvertedIndex};
use crate::inverted_index::postings;
use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::time::{Duration, Instant};

const SYNTHETIC_BOOK_ID_BASE: i32 = 900000;
const BASE_BATCH_SIZES: [usize; 7] = [25, 50, 250, 500, 1000, 5000, 10000];

pub struct TokenizedBook {
    pub id: i32,
    pub tokens: Vec<String>,
}

pub trait IndexStructure {
    fn name(&self) -> &'static str;
    fn reset(&mut self) -> BenchResult<()>;
    fn build(&mut self, books: &[TokenizedBook]) -> BenchResult<()>;
    fn prepare_query(&mut self, suite: &Suite) -> BenchResult<()>;
    fn query_postings(&self, term: &str) -> BenchResult<Vec<i32>>;
    fn add_book(&mut self, book_id: i32, tokens: &[String]) -> BenchResult<()>;
    fn storage_usage(&self) -> BenchResult<DiskUsage>;
}

pub fn run(suite: &Suite) -> BenchResult<()> {
    let books = measure_pipeline_stages(suite)?;
    if books.is_empty() {
        return Err(format!("no books in {}", suite.config().bodies_dir.display()).into());
    }
    let mut structures = index_structures(suite)?;
    for structure in structures.iter_mut() {
        run_structure_experiments(suite, structure.as_mut(), &books)
            .map_err(|error| format!("{} experiments: {error}", structure.name()))?;
    }
    Ok(())
}

fn run_structure_experiments(
    suite: &Suite,
    structure: &mut dyn IndexStructure,
    books: &[TokenizedBook],
) -> BenchResult<()> {
    log::line(&format!("--- Inverted index structure: {} ---", structure.name()));
    structure.reset()?;
    for batch_size in build_batch_sizes(books.len()) {
        let batch = build_subset(books, batch_size);
        measure_build_batch(suite, structure, &batch, batch_size)?;
    }
    structure.prepare_query(suite)?;
    let durations = run_query_workload(suite, structure)?;
    suite.record_query_statistics(&format!("query_{}", structure.name()), &durations)?;
    measure_structure_update(suite, structure, books)?;
    measure_structure_storage(suite, structure)
}

fn measure_build_batch(
    suite: &Suite,
    structure: &mut dyn IndexStructure,
    batch: &[TokenizedBook],
    batch_size: usize,
) -> BenchResult<()> {
    let measurement = measure::measure(&format!("build_{}", structure.name()), || {
        structure.build(batch)
    })?;
    log::line(&format!(
        "[build_{}] batch {}: {:.4}s",
        structure.name(),
        batch_size,
        measurement.seconds()
    ));
    suite
        .results()
        .save_scalability(&format!("build_{}", structure.name()), batch_size, &measurement)
}

fn measure_structure_update(
    suite: &Suite,
    structure: &mut dyn IndexStructure,
    books: &[TokenizedBook],
) -> BenchResult<()> {
    let new_book_id = books.last().map(|book| book.id + 1).unwrap_or_default();
    let tokens = books.first().map(|book| &book.tokens);
    suite.measure(&format!("update_{}", structure.name()), || {
        structure.add_book(new_book_id, tokens.map_or(&[], |tokens| tokens.as_slice()))
    })
    .map(|_| ())
}

fn measure_structure_storage(suite: &Suite, structure: &dyn IndexStructure) -> BenchResult<()> {
    let usage = structure.storage_usage()?;
    log::line(&format!(
        "[disk] {}: {:.4} MB, {} files, {} dirs",
        usage.path, usage.size_mb, usage.file_count, usage.dir_count
    ));
    suite.results().save_disk_usage(&usage)
}

fn index_structures(suite: &Suite) -> BenchResult<Vec<Box<dyn IndexStructure>>> {
    let mut structures: Vec<Box<dyn IndexStructure>> = vec![
        Box::new(JsonIndexStructure::new(
            suite.output_path(&["datamarts", "inverted_index.json"]),
        )),
        Box::new(FolderIndexStructure::new(suite)),
    ];
    let config = suite.config();
    if config.skip_mongo || !MongoIndex::is_available(&config.mongo_uri) {
        log::line(&format!(
            "[mongo] MongoDB skipped (disabled or not reachable at {})",
            config.mongo_uri
        ));
        return Ok(structures);
    }
    structures.push(Box::new(MongoIndexStructure {
        index: suite.connect_mongo()?,
        uri: config.mongo_uri.clone(),
        database: config.mongo_database.clone(),
        collection: config.mongo_collection.clone(),
    }));
    Ok(structures)
}

fn run_query_workload(
    suite: &Suite,
    structure: &dyn IndexStructure,
) -> BenchResult<Vec<Duration>> {
    let config = suite.config();
    let mut durations = Vec::with_capacity(config.queries.len() * config.query_repetitions);
    for _ in 0..config.query_repetitions {
        for query in &config.queries {
            let start = Instant::now();
            queries::intersect(query, |term| structure.query_postings(term))?;
            durations.push(start.elapsed());
        }
    }
    Ok(durations)
}

pub fn build_batch_sizes(book_count: usize) -> Vec<usize> {
    let mut sizes: BTreeSet<usize> = BASE_BATCH_SIZES.into();
    sizes.insert(book_count);
    sizes.into_iter().collect()
}

pub fn build_subset(books: &[TokenizedBook], batch_size: usize) -> Vec<TokenizedBook> {
    let real_count = batch_size.min(books.len());
    let mut subset: Vec<TokenizedBook> = books[..real_count]
        .iter()
        .map(|book| TokenizedBook {
            id: book.id,
            tokens: book.tokens.clone(),
        })
        .collect();
    for offset in 0..batch_size - real_count {
        subset.push(TokenizedBook {
            id: SYNTHETIC_BOOK_ID_BASE + offset as i32,
            tokens: books[offset % books.len()].tokens.clone(),
        });
    }
    subset
}

fn measure_pipeline_stages(suite: &Suite) -> BenchResult<Vec<TokenizedBook>> {
    let mut books = Vec::new();
    let tokenize = suite.measure("tokenize_books", || {
        books = load_corpus(suite)?;
        Ok(())
    })?;
    log::line(&format!(
        "[index] {} books from {}",
        books.len(),
        suite.config().bodies_dir.display()
    ));
    suite.record_throughput(&tokenize, books.len())?;
    let mut term_count = 0usize;
    suite.measure("build_postings", || {
        term_count = build_index(&books).term_count();
        Ok(())
    })?;
    log::line(&format!("[index] {term_count} unique terms"));
    Ok(books)
}

fn load_corpus(suite: &Suite) -> BenchResult<Vec<TokenizedBook>> {
    let corpus: BTreeMap<i32, Vec<String>> = corpus::load(&suite.config().bodies_dir)?;
    Ok(corpus
        .into_iter()
        .map(|(id, tokens)| TokenizedBook { id, tokens })
        .collect())
}

fn build_index(books: &[TokenizedBook]) -> InvertedIndex {
    let mut index = InvertedIndex::new();
    for book in books {
        index.add_book(book.id, &book.tokens);
    }
    index
}

fn index_map(books: &[TokenizedBook]) -> BTreeMap<i32, Vec<String>> {
    books
        .iter()
        .map(|book| (book.id, book.tokens.clone()))
        .collect()
}

struct JsonIndexStructure {
    path: PathBuf,
    loaded: InvertedIndex,
}

impl JsonIndexStructure {
    fn new(path: PathBuf) -> Self {
        Self {
            path,
            loaded: InvertedIndex::new(),
        }
    }
}

impl IndexStructure for JsonIndexStructure {
    fn name(&self) -> &'static str {
        "json_index"
    }

    fn reset(&mut self) -> BenchResult<()> {
        self.loaded = InvertedIndex::new();
        if self.path.exists() {
            std::fs::remove_file(&self.path)?;
        }
        Ok(())
    }

    fn build(&mut self, books: &[TokenizedBook]) -> BenchResult<()> {
        build_index(books).save(&self.path)?;
        Ok(())
    }

    fn prepare_query(&mut self, suite: &Suite) -> BenchResult<()> {
        let Self { path, loaded } = self;
        suite.measure("load_json_index", || {
            *loaded = json_index::load(path)?;
            Ok(())
        })?;
        Ok(())
    }

    fn query_postings(&self, term: &str) -> BenchResult<Vec<i32>> {
        Ok(self.loaded.get(term).cloned().unwrap_or_default())
    }

    fn add_book(&mut self, book_id: i32, tokens: &[String]) -> BenchResult<()> {
        json_index::add_book_to_file(book_id, tokens, &self.path)?;
        Ok(())
    }

    fn storage_usage(&self) -> BenchResult<DiskUsage> {
        DiskUsage::measure(&self.path)
    }
}

struct FolderIndexStructure {
    index_dir: PathBuf,
}

impl FolderIndexStructure {
    fn new(suite: &Suite) -> Self {
        Self {
            index_dir: suite.output_path(&["datamarts", "inverted_index"]),
        }
    }
}

impl IndexStructure for FolderIndexStructure {
    fn name(&self) -> &'static str {
        "folder_index"
    }

    fn reset(&mut self) -> BenchResult<()> {
        super::suite::reset_directory(&self.index_dir)
    }

    fn build(&mut self, books: &[TokenizedBook]) -> BenchResult<()> {
        folder_index::save(&build_index(books), &self.index_dir)?;
        Ok(())
    }

    fn prepare_query(&mut self, _suite: &Suite) -> BenchResult<()> {
        Ok(())
    }

    fn query_postings(&self, term: &str) -> BenchResult<Vec<i32>> {
        Ok(folder_index::query(term, &self.index_dir)?)
    }

    fn add_book(&mut self, book_id: i32, tokens: &[String]) -> BenchResult<()> {
        folder_index::update(book_id, tokens, &self.index_dir)?;
        Ok(())
    }

    fn storage_usage(&self) -> BenchResult<DiskUsage> {
        DiskUsage::measure(&self.index_dir)
    }
}

struct MongoIndexStructure {
    index: MongoIndex,
    uri: String,
    database: String,
    collection: String,
}

impl IndexStructure for MongoIndexStructure {
    fn name(&self) -> &'static str {
        "mongo_index"
    }

    fn reset(&mut self) -> BenchResult<()> {
        self.index.clear()
    }

    fn build(&mut self, books: &[TokenizedBook]) -> BenchResult<()> {
        self.index.save(&postings::build(&index_map(books)))
    }

    fn prepare_query(&mut self, _suite: &Suite) -> BenchResult<()> {
        Ok(())
    }

    fn query_postings(&self, term: &str) -> BenchResult<Vec<i32>> {
        self.index.query(term)
    }

    fn add_book(&mut self, book_id: i32, tokens: &[String]) -> BenchResult<()> {
        self.index.update_book(book_id, tokens)
    }

    fn storage_usage(&self) -> BenchResult<DiskUsage> {
        let stats = self.index.storage_stats()?;
        Ok(DiskUsage {
            path: format!("{}/{}.{}", self.uri, self.database, self.collection),
            size_mb: stats.storage_bytes as f64 / (1024.0 * 1024.0),
            file_count: 0,
            dir_count: 0,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tokens(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| value.to_string()).collect()
    }

    #[test]
    fn batch_sizes_sort_and_deduplicate_the_corpus_size() {
        assert_eq!(vec![25, 50, 60, 250, 500, 1000, 5000, 10000], build_batch_sizes(60));
        assert_eq!(vec![10, 25, 50, 250, 500, 1000, 5000, 10000], build_batch_sizes(10));
        assert_eq!(
            vec![25, 50, 250, 500, 600, 1000, 5000, 10000],
            build_batch_sizes(600)
        );
    }

    #[test]
    fn subset_keeps_real_books_and_fills_with_synthetic_ones() {
        let books = vec![
            TokenizedBook {
                id: 84,
                tokens: tokens(&["a"]),
            },
            TokenizedBook {
                id: 1342,
                tokens: tokens(&["b"]),
            },
        ];
        let subset = build_subset(&books, 5);
        assert_eq!(5, subset.len());
        assert_eq!(84, subset[0].id);
        assert_eq!(1342, subset[1].id);
        assert_eq!(900000, subset[2].id);
        assert_eq!(900002, subset[4].id);
        assert_eq!(tokens(&["a"]), subset[2].tokens);
        assert_eq!(tokens(&["b"]), subset[3].tokens);
    }

    #[test]
    fn subset_never_exceeds_the_corpus_when_batch_is_smaller() {
        let books = vec![TokenizedBook {
            id: 1,
            tokens: tokens(&["x"]),
        }];
        assert_eq!(1, build_subset(&books, 1).len());
        assert_eq!(1, build_subset(&books, 1)[0].id);
    }

    #[test]
    fn build_index_orders_terms_by_first_appearance() {
        let books = vec![
            TokenizedBook {
                id: 1,
                tokens: tokens(&["zebra", "apple"]),
            },
            TokenizedBook {
                id: 2,
                tokens: tokens(&["mango", "apple"]),
            },
        ];
        let index = build_index(&books);
        let terms: Vec<&str> = index.iter().map(|(term, _)| term).collect();
        assert_eq!(vec!["zebra", "apple", "mango"], terms);
        assert_eq!(Some(&vec![1, 2]), index.get("apple"));
    }
}
