use std::fs;
use std::io;
use std::path::PathBuf;

pub trait Fetcher {
    fn fetch(&self, book_id: i32) -> io::Result<String>;
}

pub struct GutenbergFetcher {
    base_url: String,
}

impl GutenbergFetcher {
    pub fn new() -> Self {
        Self {
            base_url: "https://www.gutenberg.org/cache/epub".to_string(),
        }
    }

    pub fn with_base_url(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
        }
    }
}

impl Default for GutenbergFetcher {
    fn default() -> Self {
        Self::new()
    }
}

impl Fetcher for GutenbergFetcher {
    fn fetch(&self, book_id: i32) -> io::Result<String> {
        let url = format!("{}/{book_id}/pg{book_id}.txt", self.base_url);
        println!("Downloading book {book_id} from {url}...");
        let response = reqwest::blocking::get(&url)
            .map_err(|error| io::Error::new(io::ErrorKind::Other, error.to_string()))?;
        if !response.status().is_success() {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                format!("unexpected status {} for book {book_id}", response.status()),
            ));
        }
        response
            .text()
            .map_err(|error| io::Error::new(io::ErrorKind::Other, error.to_string()))
    }
}

pub struct DirectoryFetcher {
    directory: PathBuf,
}

impl DirectoryFetcher {
    pub fn new(directory: impl Into<PathBuf>) -> Self {
        Self {
            directory: directory.into(),
        }
    }
}

impl Fetcher for DirectoryFetcher {
    fn fetch(&self, book_id: i32) -> io::Result<String> {
        fs::read_to_string(self.directory.join(format!("pg{book_id}.txt")))
    }
}
