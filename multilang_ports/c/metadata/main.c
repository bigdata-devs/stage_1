#include <stdio.h>
#include <sys/stat.h>
#include "metadata.h"

StorageBackend sqlite_create(const char *db_path);
StorageBackend postgres_create(const char *conninfo);
StorageBackend mongo_create(const char *uri_string, const char *db_name);
BookMetadata process_book(int book_id, const char *output_dir, StorageBackend *db_backend);

int main() {
    const char *output_folder = "data/test_datalake";
    StorageBackend db;

    #if defined(_WIN32)
        mkdir("data");
    #else
        mkdir("data", 0777);
    #endif

    //db = sqlite_create("data/metadata.db");
    
    
    //const char *pg_conninfo = "host=localhost port=5432 dbname=bigdata_project user=postgres password=";
    //db = postgres_create(pg_conninfo);
    
    db = mongo_create("mongodb://localhost:27017", "bigdata_project");
    

    if (db.context == NULL) {
        fprintf(stderr, "No se pudo conectar a la base de datos.\n");
        return 1;
    }

    BookMetadata result = process_book(1342, output_folder, &db);

    printf("{Language=%s, Title=%s, Author=%s, book_id=%d, Capture Date=%s}\n", 
           result.language, result.title, result.author, result.book_id, result.capture_date);

    db.close(&db);
    return 0;
}