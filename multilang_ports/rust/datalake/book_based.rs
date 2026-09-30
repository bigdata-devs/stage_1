use super::downloader::{fetch_and_save, project_root};

pub fn download(book_id: u32) -> bool {
    let base_path = project_root().join("datalake");
    let output_path = base_path.join(book_id.to_string());
    fetch_and_save(book_id, &output_path)
}