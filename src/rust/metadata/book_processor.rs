use std::fs;
use std::path::Path;
use reqwest::blocking::get;
use regex::Regex;
use chrono::Local;
use std::error::Error;
use crate::metadata::{BookMetadata, StorageBackend};

fn extract_metadata(text: &str, pattern: &str) -> String {
    let re = Regex::new(pattern).unwrap();
    if let Some(caps) = re.captures(text) {
        if let Some(matched) = caps.get(1) {
            return matched.as_str().trim().to_string();
        }
    }
    "Unknown".to_string()
}

pub fn process_book(
    book_id: i32,
    output_dir: &str,
    db_backend: &dyn StorageBackend,
) -> Result<BookMetadata, Box<dyn Error>> {
    
    let capture_date = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let url = format!("https://www.gutenberg.org/cache/epub/{}/pg{}.txt", book_id, book_id);
    
    let text = get(&url)?.text()?;

    let start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK";
    let end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK";

    if let (Some(start_idx), Some(end_idx)) = (text.find(start_marker), text.find(end_marker)) {
        let header = &text[..start_idx];
        let body = &text[start_idx..end_idx];

        let title = extract_metadata(header, r"(?i)Title:\s*([^\n\r]+)");
        let author = extract_metadata(header, r"(?i)Author:\s*([^\n\r]+)");
        let language = extract_metadata(header, r"(?i)Language:\s*([^\n\r]+)");

        let metadata = BookMetadata {
            book_id, title, author, language, capture_date,
        };

        db_backend.save(&metadata)?;

        fs::create_dir_all(output_dir)?;
        
        let header_path = Path::new(output_dir).join(format!("{}_header.txt", book_id));
        let body_path = Path::new(output_dir).join(format!("{}_body.txt", book_id));

        fs::write(header_path, header.trim())?;
        fs::write(body_path, body.trim())?;

        println!("Text files generated successfully in: {}", output_dir);
        Ok(metadata)
    } else {
        Err("Markers not found in the text.".into())
    }
}