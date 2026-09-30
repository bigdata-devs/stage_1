use super::fetcher::GutenbergFetcher;
use super::layout::Layout;
use super::store::Datalake;
use std::path::{Path, PathBuf};

const BATCH_SIZE: i32 = 1000;

pub struct BatchBased;

impl Layout for BatchBased {
    fn name(&self) -> &'static str {
        "batch_based"
    }

    fn directory(&self, root: &Path, book_id: i32) -> PathBuf {
        root.join(batch_folder_name(book_id))
    }
}

fn batch_folder_name(book_id: i32) -> String {
    let lower_bound = book_id.div_euclid(BATCH_SIZE) * BATCH_SIZE;
    let upper_bound = lower_bound + BATCH_SIZE - 1;
    format!("batch_{lower_bound}_{upper_bound}")
}

pub fn download(book_id: i32) -> bool {
    let lake = Datalake::new(super::project_root().join("datalake"), &BatchBased);
    lake.download(&GutenbergFetcher::new(), book_id)
}
