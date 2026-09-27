use postgres::{Client, NoTls};
use std::error::Error;
use crate::metadata::{BookMetadata, StorageBackend};
use std::cell::RefCell;

pub struct PostgresStorage {
    client: RefCell<Client>,
}

impl PostgresStorage {
    pub fn new(conn_string: &str) -> Result<Self, Box<dyn Error>> {
        let mut client = Client::connect(conn_string, NoTls)?;
        client.execute(
            "CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT,
                language TEXT,
                capture_date TEXT
            )",
            &[],
        )?;
        Ok(PostgresStorage {
            client: RefCell::new(client),
        })
    }
}

impl StorageBackend for PostgresStorage {
    fn save(&self, metadata: &BookMetadata) -> Result<(), Box<dyn Error>> {
        let mut client = self.client.borrow_mut();
        client.execute(
            "INSERT INTO books (book_id, title, author, language, capture_date)
             VALUES ($1, $2, $3, $4, $5)
             ON CONFLICT (book_id) DO UPDATE 
             SET title = EXCLUDED.title, author = EXCLUDED.author, 
                 language = EXCLUDED.language, capture_date = EXCLUDED.capture_date",
            &[&metadata.book_id, &metadata.title, &metadata.author, 
              &metadata.language, &metadata.capture_date],
        )?;
        println!("Metadata successfully saved to PostgreSQL.");
        Ok(())
    }
}