#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sqlite3.h>
#include "metadata.h"

static void sqlite_save(StorageBackend *self, BookMetadata *metadata) {
    sqlite3 *db = (sqlite3 *)self->context;
    
    const char *sql = "INSERT OR REPLACE INTO books (book_id, title, author, language, capture_date) VALUES (?, ?, ?, ?, ?);";
    sqlite3_stmt *stmt;

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) == SQLITE_OK) {
        sqlite3_bind_int(stmt, 1, metadata->book_id);
        sqlite3_bind_text(stmt, 2, metadata->title, -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 3, metadata->author, -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 4, metadata->language, -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 5, metadata->capture_date, -1, SQLITE_TRANSIENT);

        if (sqlite3_step(stmt) != SQLITE_DONE) {
            fprintf(stderr, "Error guardando en SQLite: %s\n", sqlite3_errmsg(db));
        } else {
            printf("Metadata successfully saved to SQLite.\n");
        }
        sqlite3_finalize(stmt);
    } else {
        fprintf(stderr, "Error preparing SQLite query: %s\n", sqlite3_errmsg(db));
    }
}

static void sqlite_close(StorageBackend *self) {
    if (self->context) {
        sqlite3_close((sqlite3 *)self->context);
    }
}

StorageBackend sqlite_create(const char *db_path) {
    StorageBackend backend;
    sqlite3 *db;
    
    if (sqlite3_open(db_path, &db) == SQLITE_OK) {
        const char *sql_create = "CREATE TABLE IF NOT EXISTS books ("
                                 "book_id INTEGER PRIMARY KEY, "
                                 "title TEXT, "
                                 "author TEXT, "
                                 "language TEXT, "
                                 "capture_date TEXT);";
        
        char *err_msg = 0;
        if (sqlite3_exec(db, sql_create, 0, 0, &err_msg) != SQLITE_OK) {
            fprintf(stderr, "Error creating SQLite table: %s\n", err_msg);
            sqlite3_free(err_msg);
        }
    } else {
        fprintf(stderr, "Error opening SQLite database: %s\n", sqlite3_errmsg(db));
        db = NULL;
    }
    
    backend.context = db;
    backend.save = sqlite_save;
    backend.close = sqlite_close;
    return backend;
}