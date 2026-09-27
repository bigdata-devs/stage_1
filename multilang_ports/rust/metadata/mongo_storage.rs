use mongodb::{sync::Client, bson::doc, options::UpdateOptions};
use std::error::Error;
use crate::metadata::{BookMetadata, StorageBackend};

pub struct MongoStorage {
    client: Client,
    db_name: String,
}

impl MongoStorage {
    pub fn new(uri: &str, db_name: &str) -> Result<Self, Box<dyn Error>> {
        let client = Client::with_uri_str(uri)?;
        Ok(MongoStorage {
            client,
            db_name: db_name.to_string(),
        })
    }
}

impl StorageBackend for MongoStorage {
    fn save(&self, metadata: &BookMetadata) -> Result<(), Box<dyn Error>> {
        let db = self.client.database(&self.db_name);
        let collection = db.collection::<mongodb::bson::Document>("books");

        let filter = doc! { "book_id": metadata.book_id };
        let update = doc! {
            "$set": {
                "title": &metadata.title,
                "author": &metadata.author,
                "language": &metadata.language,
                "capture_date": &metadata.capture_date,
            }
        };
        let options = UpdateOptions::builder().upsert(true).build();

        collection.update_one(filter, update, options)?;
        println!("Metadata successfully saved to MongoDB.");
        Ok(())
    }
}