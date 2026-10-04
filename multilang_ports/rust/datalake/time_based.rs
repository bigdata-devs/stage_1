use super::fetcher::GutenbergFetcher;
use super::layout::{locate_in, Layout, LocatedBook, BODY_SUFFIX};
use super::store::Datalake;
use chrono::Local;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

const DATE_PATTERN: &str = "%Y%m%d";
const HOUR_PATTERN: &str = "%H";

pub struct TimeBased;

impl Layout for TimeBased {
    fn name(&self) -> &'static str {
        "time_based"
    }

    fn directory(&self, root: &Path, _book_id: i32) -> PathBuf {
        let now = Local::now();
        root.join(now.format(DATE_PATTERN).to_string())
            .join(now.format(HOUR_PATTERN).to_string())
    }

    /// Probes the exact file names inside every `YYYYMMDD/HH` folder, newest
    /// first, instead of walking every stored file, like `find_time_based_book()`.
    fn locate(&self, root: &Path, book_id: i32) -> io::Result<LocatedBook> {
        hour_directories_newest_first(root)?
            .iter()
            .find_map(|hour_directory| locate_in(hour_directory, book_id).ok())
            .ok_or_else(|| {
                io::Error::new(
                    io::ErrorKind::NotFound,
                    format!("book not found: {book_id}{BODY_SUFFIX}"),
                )
            })
    }
}

/// Lists the `<root>/YYYYMMDD/HH` folders in descending order, which is
/// newest first because the names sort chronologically.
fn hour_directories_newest_first(root: &Path) -> io::Result<Vec<PathBuf>> {
    let mut hour_directories = Vec::new();
    for date_directory in subdirectories(root)? {
        hour_directories.extend(subdirectories(&date_directory)?);
    }
    hour_directories.sort_unstable_by(|left, right| right.cmp(left));
    Ok(hour_directories)
}

fn subdirectories(directory: &Path) -> io::Result<Vec<PathBuf>> {
    let mut directories = Vec::new();
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            directories.push(entry.path());
        }
    }
    Ok(directories)
}

pub fn download(book_id: i32) -> bool {
    let lake = Datalake::new(super::project_root().join("datalake"), &TimeBased);
    lake.download(&GutenbergFetcher::new(), book_id)
}
