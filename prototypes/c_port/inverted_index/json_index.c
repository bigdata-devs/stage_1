#include "json_index.h"

#include "util.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_BUCKET_COUNT 128

typedef struct {
    const char *cursor;
} JsonReader;

static void index_rehash(InvertedIndex *index, size_t bucket_count) {
    free(index->buckets);
    index->bucket_count = bucket_count;
    index->buckets = calloc(bucket_count, sizeof(size_t));
    if (index->buckets == NULL) {
        die("out of memory");
    }
    for (size_t entry_index = 0; entry_index < index->count; entry_index++) {
        const char *term = index->entries[entry_index].term;
        size_t slot = (size_t)(fnv1a_hash(term) & (bucket_count - 1));
        while (index->buckets[slot] != 0) {
            slot = (slot + 1) & (bucket_count - 1);
        }
        index->buckets[slot] = entry_index + 1;
    }
}

static void index_reserve_entry_capacity(InvertedIndex *index) {
    if (index->count < index->capacity) {
        return;
    }
    index->capacity = index->capacity == 0 ? 64 : index->capacity * 2;
    index->entries = realloc(index->entries, index->capacity * sizeof(IndexEntry));
    if (index->entries == NULL) {
        die("out of memory");
    }
}

static size_t find_slot(const InvertedIndex *index, const char *term) {
    size_t slot = (size_t)(fnv1a_hash(term) & (index->bucket_count - 1));
    while (index->buckets[slot] != 0) {
        const IndexEntry *entry = &index->entries[index->buckets[slot] - 1];
        if (strcmp(entry->term, term) == 0) {
            return slot;
        }
        slot = (slot + 1) & (index->bucket_count - 1);
    }
    return slot;
}

static IndexEntry *find_or_create_entry(InvertedIndex *index, const char *term) {
    size_t slot = find_slot(index, term);
    if (index->buckets[slot] != 0) {
        return &index->entries[index->buckets[slot] - 1];
    }
    index_reserve_entry_capacity(index);
    IndexEntry *entry = &index->entries[index->count];
    entry->term = xstrdup(term);
    entry->postings = NULL;
    entry->postings_count = 0;
    entry->last_book_id = -1;
    index->buckets[slot] = ++index->count;
    if ((index->count + 1) * 4 >= index->bucket_count * 3) {
        index_rehash(index, index->bucket_count * 2);
    }
    return entry;
}

static void append_book_id(IndexEntry *entry, int book_id) {
    if (entry->last_book_id == book_id) {
        return;
    }
    entry->postings = realloc(entry->postings, (entry->postings_count + 1) * sizeof(int));
    if (entry->postings == NULL) {
        die("out of memory");
    }
    entry->postings[entry->postings_count++] = book_id;
    entry->last_book_id = book_id;
}

static void write_postings(FILE *stream, const IndexEntry *entry) {
    if (entry->postings_count == 0) {
        fputs("[]", stream);
        return;
    }
    fputs("[\n", stream);
    for (size_t position = 0; position < entry->postings_count; position++) {
        fprintf(stream, "    %d", entry->postings[position]);
        fputs(position + 1 < entry->postings_count ? ",\n" : "\n", stream);
    }
    fputs("  ]", stream);
}

static void skip_spaces(JsonReader *reader) {
    while (isspace((unsigned char)*reader->cursor)) {
        reader->cursor++;
    }
}

static void expect_char(JsonReader *reader, char expected) {
    if (*reader->cursor != expected) {
        die("invalid index file");
    }
    reader->cursor++;
}

static char *parse_string(JsonReader *reader) {
    expect_char(reader, '"');
    const char *start = reader->cursor;
    while (*reader->cursor != '"') {
        reader->cursor++;
    }
    size_t length = (size_t)(reader->cursor - start);
    char *value = malloc(length + 1);
    if (value == NULL) {
        die("out of memory");
    }
    memcpy(value, start, length);
    value[length] = '\0';
    reader->cursor++;
    return value;
}

static int *parse_postings(JsonReader *reader, size_t *out_count) {
    expect_char(reader, '[');
    skip_spaces(reader);
    if (*reader->cursor == ']') {
        reader->cursor++;
        *out_count = 0;
        return NULL;
    }
    size_t capacity = 8;
    size_t count = 0;
    int *values = malloc(capacity * sizeof(int));
    if (values == NULL) {
        die("out of memory");
    }
    while (1) {
        skip_spaces(reader);
        if (count == capacity) {
            capacity *= 2;
            values = realloc(values, capacity * sizeof(int));
            if (values == NULL) {
                die("out of memory");
            }
        }
        values[count++] = (int)strtol(reader->cursor, (char **)&reader->cursor, 10);
        skip_spaces(reader);
        if (*reader->cursor == ']') {
            reader->cursor++;
            break;
        }
        expect_char(reader, ',');
    }
    *out_count = count;
    return values;
}

static void append_loaded_entry(InvertedIndex *index, char *term, int *postings, size_t postings_count) {
    index_reserve_entry_capacity(index);
    IndexEntry *entry = &index->entries[index->count++];
    entry->term = term;
    entry->postings = postings;
    entry->postings_count = postings_count;
    entry->last_book_id = -1;
}

static size_t fitting_bucket_count(size_t entry_count) {
    size_t needed = entry_count * 2 + 16;
    size_t bucket_count = INITIAL_BUCKET_COUNT;
    while (bucket_count < needed) {
        bucket_count *= 2;
    }
    return bucket_count;
}

InvertedIndex *index_create(void) {
    InvertedIndex *index = calloc(1, sizeof(InvertedIndex));
    if (index == NULL) {
        die("out of memory");
    }
    index_rehash(index, INITIAL_BUCKET_COUNT);
    return index;
}

void index_destroy(InvertedIndex *index) {
    for (size_t entry_index = 0; entry_index < index->count; entry_index++) {
        free(index->entries[entry_index].term);
        free(index->entries[entry_index].postings);
    }
    free(index->entries);
    free(index->buckets);
    free(index);
}

void index_add_book(InvertedIndex *index, int book_id, const TokenList *tokens) {
    for (size_t token_index = 0; token_index < tokens->count; token_index++) {
        IndexEntry *entry = find_or_create_entry(index, tokens->items[token_index]);
        append_book_id(entry, book_id);
    }
}

void index_save(const InvertedIndex *index, const char *path) {
    FILE *stream = fopen(path, "w");
    if (stream == NULL) {
        die_io(path);
    }
    fputs("{\n", stream);
    for (size_t entry_index = 0; entry_index < index->count; entry_index++) {
        const IndexEntry *entry = &index->entries[entry_index];
        fprintf(stream, "  \"%s\": ", entry->term);
        write_postings(stream, entry);
        fputs(entry_index + 1 < index->count ? ",\n" : "\n", stream);
    }
    fputc('}', stream);
    if (fclose(stream) != 0) {
        die_io(path);
    }
}

InvertedIndex *index_load(const char *path) {
    char *json = read_text_file(path);
    JsonReader reader = {json};
    InvertedIndex *index = index_create();
    expect_char(&reader, '{');
    skip_spaces(&reader);
    if (*reader.cursor != '}') {
        while (1) {
            skip_spaces(&reader);
            char *term = parse_string(&reader);
            skip_spaces(&reader);
            expect_char(&reader, ':');
            skip_spaces(&reader);
            size_t postings_count = 0;
            int *postings = parse_postings(&reader, &postings_count);
            append_loaded_entry(index, term, postings, postings_count);
            skip_spaces(&reader);
            if (*reader.cursor == '}') {
                reader.cursor++;
                break;
            }
            expect_char(&reader, ',');
        }
    } else {
        reader.cursor++;
    }
    index_rehash(index, fitting_bucket_count(index->count));
    free(json);
    return index;
}

const int *index_query(const InvertedIndex *index, const char *term, size_t *out_count) {
    size_t slot = (size_t)(fnv1a_hash(term) & (index->bucket_count - 1));
    while (index->buckets[slot] != 0) {
        const IndexEntry *entry = &index->entries[index->buckets[slot] - 1];
        if (strcmp(entry->term, term) == 0) {
            *out_count = entry->postings_count;
            return entry->postings;
        }
        slot = (slot + 1) & (index->bucket_count - 1);
    }
    *out_count = 0;
    return NULL;
}
