#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libpq-fe.h>
#include "metadata.h"

static void postgres_save(StorageBackend *self, BookMetadata *metadata) {
    PGconn *conn = (PGconn *)self->context;
    
    const char *sql = "INSERT INTO books_metadata (book_id, title, author, language, capture_date) "
                      "VALUES ($1, $2, $3, $4, $5) "
                      "ON CONFLICT (book_id) DO UPDATE SET "
                      "title = EXCLUDED.title, author = EXCLUDED.author, "
                      "language = EXCLUDED.language, capture_date = EXCLUDED.capture_date;";

    char book_id_str[32];
    snprintf(book_id_str, sizeof(book_id_str), "%d", metadata->book_id);

    const char *paramValues[5] = { 
        book_id_str, metadata->title, metadata->author, 
        metadata->language, metadata->capture_date 
    };

    PGresult *res = PQexecParams(conn, sql, 5, NULL, paramValues, NULL, NULL, 0);
    
    if (PQresultStatus(res) != PGRES_COMMAND_OK) {
        fprintf(stderr, "Error saving to PostgreSQL: %s\n", PQerrorMessage(conn));
    } else {
        printf("Metadata successfully saved in PostgreSQL..\n");
    }
    PQclear(res);
}

static void postgres_close(StorageBackend *self) {
    if (self->context) {
        PQfinish((PGconn *)self->context);
    }
}

StorageBackend postgres_create(const char *conninfo) {
    StorageBackend backend;
    PGconn *conn = PQconnectdb(conninfo);

    if (PQstatus(conn) == CONNECTION_OK) {
        const char *sql_create = "CREATE TABLE IF NOT EXISTS books_metadata ("
                                 "book_id INTEGER PRIMARY KEY, "
                                 "title VARCHAR(255), author VARCHAR(255), "
                                 "language VARCHAR(50), capture_date VARCHAR(50));";
        PGresult *res = PQexec(conn, sql_create);
        PQclear(res);
    } else {
        fprintf(stderr, "PostgreSQL connection error: %s\n", PQerrorMessage(conn));
    }

    backend.context = conn;
    backend.save = postgres_save;
    backend.close = postgres_close;
    return backend;
}