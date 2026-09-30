use super::fetcher::GutenbergFetcher;
use super::layout::Layout;
use super::store::Datalake;
use std::path::{Path, PathBuf};

pub struct BookBased;

impl Layout for BookBased {
    fn name(&self) -> &'static str {
        "book_based"
    }

    fn directory(&self, root: &Path, book_id: i32) -> PathBuf {
        root.join(book_id.to_string())
    }
}

pub fn download(book_id: i32) -> bool {
    let lake = Datalake::new(super::project_root().join("datalake"), BookBased);
    lake.download(&GutenbergFetcher::new(), book_id)
}
