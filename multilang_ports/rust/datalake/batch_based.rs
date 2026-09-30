use super::downloader::{fetch_and_save, project_root};

pub fn download(book_id: u32, batch_size: u32) -> bool {
    let base_path = project_root().join("datalake");
    let lower_bound = (book_id / batch_size) * batch_size;
    let upper_bound = lower_bound + batch_size - 1;
    
    let dir_name = format!("batch_{}_{}", lower_bound, upper_bound);
    let output_path = base_path.join(dir_name);
    fetch_and_save(book_id, &output_path)
}