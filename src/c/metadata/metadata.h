#ifndef METADATA_H
#define METADATA_H

typedef struct {
    int book_id;
    char title[256];
    char author[256];
    char language[64];
    char capture_date[64];
} BookMetadata;

typedef struct StorageBackend {
    void *context;
    void (*save)(struct StorageBackend *self, BookMetadata *metadata);
    void (*close)(struct StorageBackend *self);
} StorageBackend;

#endif