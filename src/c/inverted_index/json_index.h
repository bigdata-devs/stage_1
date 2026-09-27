#ifndef JSON_INDEX_H
#define JSON_INDEX_H

#include "text_processor.h"

#include <stddef.h>

typedef struct {
    char *term;
    int *postings;
    size_t postings_count;
    int last_book_id;
} IndexEntry;

typedef struct {
    IndexEntry *entries;
    size_t count;
    size_t capacity;
    size_t *buckets;
    size_t bucket_count;
} InvertedIndex;

InvertedIndex *index_create(void);
void index_destroy(InvertedIndex *index);
void index_add_book(InvertedIndex *index, int book_id, const TokenList *tokens);
void index_save(const InvertedIndex *index, const char *path);
InvertedIndex *index_load(const char *path);
const int *index_query(const InvertedIndex *index, const char *term, size_t *out_count);

#endif
