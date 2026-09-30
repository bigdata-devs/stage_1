#include <stdio.h>
#include <stdlib.h>
#include <bson/bson.h>
#include <mongoc/mongoc.h>
#include "metadata.h"

typedef struct {
    mongoc_client_t *client;
    mongoc_collection_t *collection;
} MongoContext;

static void mongo_save(StorageBackend *self, BookMetadata *metadata) {
    MongoContext *ctx = (MongoContext *)self->context;
    bson_error_t error;

    bson_t *query = BCON_NEW("book_id", BCON_INT32(metadata->book_id));

    bson_t *update = BCON_NEW(
        "$set", "{",
            "book_id", BCON_INT32(metadata->book_id),
            "Title", BCON_UTF8(metadata->title),
            "Author", BCON_UTF8(metadata->author),
            "Language", BCON_UTF8(metadata->language),
            "Capture Date", BCON_UTF8(metadata->capture_date),
        "}"
    );

    bson_t *opts = BCON_NEW("upsert", BCON_BOOL(true));

    if (mongoc_collection_update_one(ctx->collection, query, update, opts, NULL, &error)) {
        printf("Metadata successfully saved to MongoDB.\n");
    } else {
        fprintf(stderr, "Error saving to MongoDB: %s\n", error.message);
    }

    bson_destroy(query);
    bson_destroy(update);
    bson_destroy(opts);
}

static void mongo_close(StorageBackend *self) {
    if (self->context) {
        MongoContext *ctx = (MongoContext *)self->context;
        mongoc_collection_destroy(ctx->collection);
        mongoc_client_destroy(ctx->client);
        mongoc_cleanup();
        free(ctx);
    }
}

StorageBackend mongo_create(const char *uri_string, const char *db_name) {
    StorageBackend backend;
    mongoc_init();

    bson_error_t error;
    mongoc_uri_t *uri = mongoc_uri_new_with_error(uri_string, &error);
    
    if (!uri) {
        fprintf(stderr, "Failed to parse MongoDB URI: %s\n", error.message);
        backend.context = NULL;
        return backend;
    }

    mongoc_client_t *client = mongoc_client_new_from_uri(uri);
    mongoc_uri_destroy(uri);
    mongoc_collection_t *collection = mongoc_client_get_collection(client, db_name, "books_metadata");

    MongoContext *ctx = malloc(sizeof(MongoContext));
    ctx->client = client;
    ctx->collection = collection;

    backend.context = ctx;
    backend.save = mongo_save;
    backend.close = mongo_close;
    return backend;
}