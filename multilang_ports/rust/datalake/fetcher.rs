use std::fs;
use std::io;
use std::path::PathBuf;
use std::time::Duration;

pub trait Fetcher {
    fn fetch(&self, book_id: i32) -> io::Result<String>;
}

/// Downloads books through one pooled `reqwest` client, so every book after
/// the first reuses the same TLS connection, exactly as Go (`http.Client`),
/// Java (`HttpClient`) and the Python `requests.Session` do. Without the pool
/// each book would pay a fresh handshake, which measures the TLS cost instead
/// of the download.
pub struct GutenbergFetcher {
    base_url: String,
    client: reqwest::blocking::Client,
}

impl GutenbergFetcher {
    pub fn new() -> Self {
        Self::with_base_url("https://www.gutenberg.org/cache/epub")
    }

    pub fn with_base_url(base_url: impl Into<String>) -> Self {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(60))
            .build()
            .unwrap_or_else(|_| reqwest::blocking::Client::new());
        Self {
            base_url: base_url.into(),
            client,
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
        let response = self
            .client
            .get(&url)
            .send()
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
