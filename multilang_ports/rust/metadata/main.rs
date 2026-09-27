mod metadata;
mod sqlite_storage;
mod postgres_storage;
mod mongo_storage;
mod book_processor;

use sqlite_storage::SqliteStorage;
use postgres_storage::PostgresStorage;
use mongo_storage::MongoStorage;
use metadata::StorageBackend;
use std::fs;

fn main() {
    let output_folder = "data/test_datalake";
    
    if let Err(e) = fs::create_dir_all("data") {
        eprintln!("Error creando carpeta data: {}", e);
        return;
    }

    //let db = SqliteStorage::new("data/metadata.db").unwrap();
    //let backend: &dyn StorageBackend = &db;

    // let pg_conn = "host=localhost port=5432 user=postgres password=TU_CONTRASENA dbname=bigdata_project";
    // let db = PostgresStorage::new(pg_conn).unwrap();
    // let backend: &dyn StorageBackend = &db;

    let db = MongoStorage::new("mongodb://localhost:27017", "bigdata_project").unwrap();
    let backend: &dyn StorageBackend = &db;

    match book_processor::process_book(1342, output_folder, backend) {
        Ok(result) => {
            println!("{{Language={}, Title={}, Author={}, book_id={}, Capture Date={}}}",
                result.language, result.title, result.author, result.book_id, result.capture_date
            );
        }
        Err(e) => eprintln!("Error processing the book: {}", e),
    }
}