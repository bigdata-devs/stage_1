pub mod batch_based;
pub mod book_based;
pub mod fetcher;
pub mod layout;
pub mod splitter;
pub mod store;
pub mod time_based;

use layout::Layout;
use std::path::PathBuf;

pub fn project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf()
}

pub fn standard_layouts() -> Vec<Box<dyn Layout>> {
    vec![
        Box::new(time_based::TimeBased),
        Box::new(book_based::BookBased),
        Box::new(batch_based::BatchBased),
    ]
}
