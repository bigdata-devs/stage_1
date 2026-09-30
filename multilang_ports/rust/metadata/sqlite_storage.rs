use rusqlite::{params, Connection};
use std::error::Error;
use crate::metadata::{BookMetadata, StorageBackend};

pub struct SqliteStorage {
    conn: Connection,
}

impl SqliteStorage {
    pub fn new(db_path: &str) -> Result<Self, Box<dyn Error>> {
        let conn = Connection::open(db_path)?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT,
                language TEXT,
                capture_date TEXT
            )",
            [],
        )?;
        Ok(SqliteStorage { conn })
    }
}

impl StorageBackend for SqliteStorage {
    fn save(&self, metadata: &BookMetadata) -> Result<(), Box<dyn Error>> {
        self.conn.execute(
            "INSERT OR REPLACE INTO books (book_id, title, author, language, capture_date)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                metadata.book_id, metadata.title, metadata.author,
                metadata.language, metadata.capture_date
            ],
        )?;
        println!("Metadata successfully saved to SQLite.");
        Ok(())
    }
}