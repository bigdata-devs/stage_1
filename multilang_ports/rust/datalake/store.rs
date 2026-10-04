use super::fetcher::Fetcher;
use super::layout::{Layout, LocatedBook, BODY_SUFFIX, HEADER_SUFFIX};
use std::collections::{BTreeSet, HashSet};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

pub struct Datalake<'a> {
    root: PathBuf,
    layout: &'a dyn Layout,
}

impl<'a> Datalake<'a> {
    pub fn new(root: impl Into<PathBuf>, layout: &'a dyn Layout) -> Self {
        Self {
            root: root.into(),
            layout,
        }
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn store(&self, book_id: i32, header: &str, body: &str) -> io::Result<PathBuf> {
        let directory = self.layout.directory(&self.root, book_id);
        fs::create_dir_all(&directory)?;
        fs::write(directory.join(format!("{book_id}{BODY_SUFFIX}")), body)?;
        fs::write(directory.join(format!("{book_id}{HEADER_SUFFIX}")), header)?;
        Ok(directory)
    }

    pub fn locate(&self, book_id: i32) -> io::Result<LocatedBook> {
        self.layout.locate(&self.root, book_id)
    }

    pub fn download(&self, fetcher: &dyn Fetcher, book_id: i32) -> bool {
        self.try_download(fetcher, book_id).unwrap_or_else(|error| {
            eprintln!("Book {book_id} failed: {error}");
            false
        })
    }

    fn try_download(&self, fetcher: &dyn Fetcher, book_id: i32) -> io::Result<bool> {
        let text = fetcher.fetch(book_id)?;
        let split = super::splitter::split(&text)?;
        self.store(book_id, &split.header, &split.body)?;
        Ok(true)
    }
}

pub fn list_book_ids(root: &Path) -> io::Result<Vec<i32>> {
    if !root.is_dir() {
        return Ok(Vec::new());
    }
    let mut complete = BTreeSet::new();
    collect_complete_book_ids(root, &mut complete)?;
    Ok(complete.into_iter().collect())
}

pub fn pending_book_ids(root: &Path, known: &[i32]) -> io::Result<Vec<i32>> {
    let known: HashSet<i32> = known.iter().copied().collect();
    Ok(list_book_ids(root)?
        .into_iter()
        .filter(|book_id| !known.contains(book_id))
        .collect())
}

fn collect_complete_book_ids(directory: &Path, complete: &mut BTreeSet<i32>) -> io::Result<()> {
    for entry in fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            collect_complete_book_ids(&path, complete)?;
            continue;
        }
        if let Some(book_id) = complete_book_id(&path) {
            complete.insert(book_id);
        }
    }
    Ok(())
}

fn complete_book_id(path: &Path) -> Option<i32> {
    let name = path.file_name()?.to_str()?;
    let book_id = name.strip_suffix(BODY_SUFFIX)?.parse().ok()?;
    let header = path.with_file_name(format!("{book_id}{HEADER_SUFFIX}"));
    header.is_file().then_some(book_id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::datalake::batch_based::BatchBased;
    use crate::datalake::book_based::BookBased;
    use crate::datalake::fetcher::DirectoryFetcher;
    use crate::datalake::time_based::TimeBased;
    use chrono::Local;
    use std::path::PathBuf;

    const RAW_BOOK: &str = "Preamble line.\n\n\
        *** START OF THE PROJECT GUTENBERG EBOOK Frankenstein ***\n\
        The body text.\n\
        *** END OF THE PROJECT GUTENBERG EBOOK Frankenstein ***\n";

    fn temp_root(label: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!(
            "stage1_rust_datalake_{label}_{}",
            std::process::id()
        ));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(&root).unwrap();
        root
    }

    #[test]
    fn store_writes_both_files_into_the_derived_directory() {
        let root = temp_root("store_book");
        let lake = Datalake::new(&root, &BookBased);
        let directory = lake.store(84, "header", "body").unwrap();
        assert_eq!(root.join("84"), directory);
        assert_eq!("body", fs::read_to_string(directory.join("84_body.txt")).unwrap());
        assert_eq!("header", fs::read_to_string(directory.join("84_header.txt")).unwrap());
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn batch_based_directory_covers_thousand_book_blocks() {
        let root = temp_root("store_batch");
        let lake = Datalake::new(&root, &BatchBased);
        let directory = lake.store(1500, "header", "body").unwrap();
        assert_eq!(root.join("batch_1000_1999"), directory);
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn time_based_store_writes_under_date_and_hour_directories() {
        let root = temp_root("store_time");
        let now = Local::now();
        let lake = Datalake::new(&root, &TimeBased);
        let directory = lake.store(11, "header", "body").unwrap();
        let expected = root
            .join(now.format("%Y%m%d").to_string())
            .join(now.format("%H").to_string());
        assert_eq!(expected, directory);
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn locate_returns_both_paths_when_the_book_is_stored() {
        let root = temp_root("locate_ok");
        let lake = Datalake::new(&root, &BookBased);
        lake.store(84, "header", "body").unwrap();
        let book = lake.locate(84).unwrap();
        assert_eq!(root.join("84/84_body.txt"), book.body_path);
        assert_eq!(root.join("84/84_header.txt"), book.header_path);
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn locate_fails_when_the_book_was_never_stored() {
        let root = temp_root("locate_missing");
        let lake = Datalake::new(&root, &BookBased);
        assert!(lake.locate(84).is_err());
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn time_based_locate_returns_the_newest_stored_copy() {
        let root = temp_root("locate_newest");
        let old_directory = root.join("20200101").join("00");
        let new_directory = root.join("20990101").join("00");
        for directory in [&old_directory, &new_directory] {
            fs::create_dir_all(directory).unwrap();
            fs::write(directory.join("42_body.txt"), "body").unwrap();
            fs::write(directory.join("42_header.txt"), "header").unwrap();
        }
        let book = TimeBased.locate(&root, 42).unwrap();
        assert_eq!(new_directory.join("42_body.txt"), book.body_path);
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn time_based_locate_skips_newer_incomplete_copies() {
        let root = temp_root("locate_incomplete");
        let old_directory = root.join("20200101").join("00");
        let new_directory = root.join("20990101").join("00");
        for directory in [&old_directory, &new_directory] {
            fs::create_dir_all(directory).unwrap();
            fs::write(directory.join("42_body.txt"), "body").unwrap();
            fs::write(directory.join("42_header.txt"), "header").unwrap();
        }
        fs::remove_file(new_directory.join("42_header.txt")).unwrap();
        let book = TimeBased.locate(&root, 42).unwrap();
        assert_eq!(old_directory.join("42_body.txt"), book.body_path);
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn time_based_locate_only_probes_hour_directories() {
        let root = temp_root("locate_depth");
        let lake = Datalake::new(&root, &BookBased);
        lake.store(42, "header", "body").unwrap();
        let nested = root.join("20200101").join("00").join("nested");
        fs::create_dir_all(&nested).unwrap();
        fs::write(nested.join("42_body.txt"), "body").unwrap();
        fs::write(nested.join("42_header.txt"), "header").unwrap();
        assert!(TimeBased.locate(&root, 42).is_err());
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn list_book_ids_returns_sorted_numeric_ids_and_skips_incomplete() {
        let root = temp_root("list_ids");
        let lake = Datalake::new(&root, &BookBased);
        lake.store(1342, "header", "body").unwrap();
        lake.store(11, "header", "body").unwrap();
        fs::write(root.join("99_body.txt"), "body").unwrap();
        fs::write(root.join("notes_body.txt"), "body").unwrap();
        assert_eq!(vec![11, 1342], list_book_ids(&root).unwrap());
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn pending_book_ids_excludes_the_known_ones() {
        let root = temp_root("pending");
        let lake = Datalake::new(&root, &BookBased);
        lake.store(1, "header", "body").unwrap();
        lake.store(2, "header", "body").unwrap();
        lake.store(3, "header", "body").unwrap();
        assert_eq!(vec![3], pending_book_ids(&root, &[1, 2]).unwrap());
        fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn download_stores_header_and_body_through_a_directory_fetcher() {
        let root = temp_root("download_ok");
        let raw = temp_root("download_raw");
        fs::write(raw.join("pg7.txt"), RAW_BOOK).unwrap();
        let lake = Datalake::new(&root, &BookBased);
        assert!(lake.download(&DirectoryFetcher::new(&raw), 7));
        assert_eq!("The body text.", fs::read_to_string(root.join("7/7_body.txt")).unwrap());
        assert!(fs::read_to_string(root.join("7/7_header.txt"))
            .unwrap()
            .contains("Preamble line."));
        fs::remove_dir_all(&root).unwrap();
        fs::remove_dir_all(&raw).unwrap();
    }

    #[test]
    fn download_reports_books_without_gutenberg_markers() {
        let root = temp_root("download_bad");
        let raw = temp_root("download_bad_raw");
        fs::write(raw.join("pg7.txt"), "no markers here").unwrap();
        let lake = Datalake::new(&root, &BookBased);
        assert!(!lake.download(&DirectoryFetcher::new(&raw), 7));
        assert!(!root.join("7/7_body.txt").exists());
        fs::remove_dir_all(&root).unwrap();
        fs::remove_dir_all(&raw).unwrap();
    }
}
