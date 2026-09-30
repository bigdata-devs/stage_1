use std::fs;
use std::path::{Path, PathBuf};

const START_MARKER: &str = "*** START OF THE PROJECT GUTENBERG EBOOK";
const END_MARKER: &str = "*** END OF THE PROJECT GUTENBERG EBOOK";

pub fn project_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf()
}

pub fn fetch_and_save(book_id: u32, output_path: &Path) -> bool {
    if fs::create_dir_all(output_path).is_err() { return false; }
    
    let url = format!("https://www.gutenberg.org/cache/epub/{}/pg{}.txt", book_id, book_id);
    println!("Downloading book {} from {}...", book_id, url);

    let response = match reqwest::blocking::get(&url) {
        Ok(res) if res.status().is_success() => res,
        _ => {
            println!("Error downloading book {}", book_id);
            return false;
        }
    };

    let text = response.text().unwrap_or_default();
    
    let start_idx = text.find(START_MARKER);
    let end_idx = text.find(END_MARKER);

    if start_idx.is_none() || end_idx.is_none() {
        println!("Invalid format for book {}", book_id);
        return false;
    }

    let start = start_idx.unwrap();
    let header = text[..start].trim();
    
    let body_start = start + text[start..].find('\n').unwrap_or(0) + 1;
    let body = text[body_start..end_idx.unwrap()].trim();

    let body_path = output_path.join(format!("{}_body.txt", book_id));
    let header_path = output_path.join(format!("{}_header.txt", book_id));

    fs::write(body_path, body).is_ok() && fs::write(header_path, header).is_ok()
}