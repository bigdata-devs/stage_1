use crate::inverted_index::json_index::InvertedIndex;
use crate::inverted_index::postings::unique_terms;
use mongodb::bson::{doc, Bson, Document};
use mongodb::options::{ClientOptions, IndexOptions, InsertManyOptions, UpdateOptions};
use mongodb::sync::{Client, Collection, Database};
use mongodb::IndexModel;
use std::error::Error;
use std::time::Duration;

pub const DEFAULT_URI: &str = "mongodb://localhost:27017";
pub const DEFAULT_DATABASE: &str = "search_engine";
pub const DEFAULT_COLLECTION: &str = "inverted_index";

const SERVER_SELECTION_TIMEOUT: Duration = Duration::from_secs(2);

pub type MongoResult<T> = Result<T, Box<dyn Error>>;

pub struct MongoStorageStats {
    pub documents: i64,
    pub data_bytes: i64,
    pub storage_bytes: i64,
    pub index_bytes: i64,
}

pub struct MongoIndex {
    database: Database,
    collection: Collection<Document>,
    collection_name: String,
}

impl MongoIndex {
    pub fn is_available(uri: &str) -> bool {
        probe(uri).unwrap_or(false)
    }

    pub fn connect(uri: &str, database_name: &str, collection_name: &str) -> MongoResult<Self> {
        let client = Client::with_options(connection_options(uri)?)?;
        let database = client.database(database_name);
        let collection: Collection<Document> = database.collection(collection_name);
        collection.create_index(term_index_model(), None)?;
        Ok(Self {
            database,
            collection,
            collection_name: collection_name.to_string(),
        })
    }

    pub fn clear(&self) -> MongoResult<()> {
        self.collection.delete_many(Document::new(), None)?;
        Ok(())
    }

    pub fn save(&self, index: &InvertedIndex) -> MongoResult<()> {
        self.clear()?;
        const INSERT_CHUNK_SIZE: usize = 5_000;
        let mut chunk: Vec<Document> = Vec::with_capacity(INSERT_CHUNK_SIZE);
        for (term, postings) in index.iter() {
            chunk.push(doc! { "term": term, "postings": postings });
            if chunk.len() == INSERT_CHUNK_SIZE {
                self.insert_documents(&chunk)?;
                chunk.clear();
            }
        }
        self.insert_documents(&chunk)
    }

    fn insert_documents(&self, documents: &[Document]) -> MongoResult<()> {
        if documents.is_empty() {
            return Ok(());
        }
        let options = InsertManyOptions::builder().ordered(false).build();
        self.collection.insert_many(documents, Some(options))?;
        Ok(())
    }

    pub fn query(&self, term: &str) -> MongoResult<Vec<i32>> {
        let Some(document) = self.collection.find_one(doc! { "term": term }, None)? else {
            return Ok(Vec::new());
        };
        Ok(document
            .get("postings")
            .and_then(Bson::as_array)
            .map(|array| array.iter().filter_map(as_book_id).collect())
            .unwrap_or_default())
    }

    pub fn update_book(&self, book_id: i32, tokens: &[String]) -> MongoResult<()> {
        let options = UpdateOptions::builder().upsert(true).build();
        for term in unique_terms(tokens) {
            self.collection.update_one(
                doc! { "term": term },
                vec![book_update_pipeline(book_id)],
                options.clone(),
            )?;
        }
        Ok(())
    }

    pub fn storage_stats(&self) -> MongoResult<MongoStorageStats> {
        let stats = self
            .database
            .run_command(doc! { "collStats": &self.collection_name }, None)?;
        Ok(MongoStorageStats {
            documents: as_i64(&stats, "count"),
            data_bytes: as_i64(&stats, "size"),
            storage_bytes: as_i64(&stats, "storageSize"),
            index_bytes: as_i64(&stats, "totalIndexSize"),
        })
    }
}

fn probe(uri: &str) -> MongoResult<bool> {
    let client = Client::with_options(connection_options(uri)?)?;
    client.database("admin").run_command(doc! { "ping": 1 }, None)?;
    Ok(true)
}

fn connection_options(uri: &str) -> MongoResult<ClientOptions> {
    let mut options = ClientOptions::parse(uri)?;
    options.server_selection_timeout = Some(SERVER_SELECTION_TIMEOUT);
    Ok(options)
}

fn term_index_model() -> IndexModel {
    IndexModel::builder()
        .keys(doc! { "term": 1 })
        .options(IndexOptions::builder().unique(true).build())
        .build()
}

fn book_update_pipeline(book_id: i32) -> Document {
    doc! {
        "$set": {
            "postings": {
                "$sortArray": {
                    "input": {
                        "$setUnion": [
                            { "$ifNull": ["$postings", Bson::Array(Vec::new())] },
                            [book_id],
                        ]
                    },
                    "sortBy": 1,
                }
            }
        }
    }
}

fn as_book_id(bson: &Bson) -> Option<i32> {
    bson.as_i32()
        .or_else(|| bson.as_i64().map(|value| value as i32))
}

fn as_i64(document: &Document, field: &str) -> i64 {
    document
        .get(field)
        .and_then(Bson::as_i64)
        .or_else(|| document.get(field).and_then(Bson::as_i32).map(i64::from))
        .or_else(|| document.get(field).and_then(Bson::as_f64).map(|value| value as i64))
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pipeline_upserts_sorted_unique_postings() {
        let pipeline = book_update_pipeline(9);
        let set = pipeline.get("$set").and_then(Bson::as_document).unwrap();
        let postings = set.get("postings").and_then(Bson::as_document).unwrap();
        let sort = postings.get("$sortArray").and_then(Bson::as_document).unwrap();
        assert_eq!(Some(&Bson::Int32(1)), sort.get("sortBy"));
        let union = sort
            .get("input")
            .and_then(Bson::as_document)
            .and_then(|input| input.get("$setUnion"))
            .and_then(Bson::as_array)
            .unwrap();
        assert_eq!(2, union.len());
    }

    #[test]
    fn available_server_is_detected_and_bookings_round_trip() {
        if !MongoIndex::is_available(DEFAULT_URI) {
            eprintln!("MongoDB is not available at {DEFAULT_URI}; skipping");
            return;
        }
        let client = Client::with_options(connection_options(DEFAULT_URI).unwrap()).unwrap();
        client
            .database("stage1_rust_test")
            .run_command(doc! { "dropDatabase": 1 }, None)
            .unwrap();
        let index = MongoIndex::connect(DEFAULT_URI, "stage1_rust_test", "inverted_index").unwrap();
        let mut books = InvertedIndex::new();
        books.add_book(11, &vec!["alpha".to_string(), "beta".to_string()]);
        books.add_book(84, &vec!["beta".to_string()]);
        index.save(&books).unwrap();
        assert_eq!(vec![11], index.query("alpha").unwrap());
        assert_eq!(vec![11, 84], index.query("beta").unwrap());
        assert!(index.query("missing").unwrap().is_empty());

        index.update_book(4, &vec!["alpha".to_string(), "gamma".to_string()]).unwrap();
        assert_eq!(vec![4, 11], index.query("alpha").unwrap());
        assert_eq!(vec![4], index.query("gamma").unwrap());

        let stats = index.storage_stats().unwrap();
        assert!(stats.storage_bytes > 0);
        assert!(stats.documents >= 3);
        index.clear().unwrap();
        assert!(index.query("alpha").unwrap().is_empty());
    }
}
