use std::error::Error;

pub struct BookMetadata {
    pub book_id: i32,
    pub title: String,
    pub author: String,
    pub language: String,
    pub capture_date: String,
}

pub trait StorageBackend {
    fn save(&self, metadata: &BookMetadata) -> Result<(), Box<dyn Error>>;
}