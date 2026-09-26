#include "json_index.h"
#include "text_processor.h"
#include "util.h"

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BODY_SUFFIX "_body.txt"
#define MAX_PATH_LENGTH 4096

static int compare_ints(const void *left, const void *right) {
    int left_value = *(const int *)left;
    int right_value = *(const int *)right;
    return (left_value > right_value) - (left_value < right_value);
}

static int has_body_suffix(const char *name) {
    size_t name_length = strlen(name);
    size_t suffix_length = strlen(BODY_SUFFIX);
    return name_length > suffix_length
        && strcmp(name + name_length - suffix_length, BODY_SUFFIX) == 0;
}

static int *discover_book_ids(const char *directory, size_t *out_count) {
    DIR *stream = opendir(directory);
    if (stream == NULL) {
        die_io(directory);
    }
    size_t capacity = 16;
    size_t count = 0;
    int *book_ids = malloc(capacity * sizeof(int));
    if (book_ids == NULL) {
        die("out of memory");
    }
    struct dirent *entry;
    while ((entry = readdir(stream)) != NULL) {
        if (!has_body_suffix(entry->d_name)) {
            continue;
        }
        if (count == capacity) {
            capacity *= 2;
            book_ids = realloc(book_ids, capacity * sizeof(int));
            if (book_ids == NULL) {
                die("out of memory");
            }
        }
        book_ids[count++] = (int)strtol(entry->d_name, NULL, 10);
    }
    closedir(stream);
    qsort(book_ids, count, sizeof(int), compare_ints);
    *out_count = count;
    return book_ids;
}

static void build_index(const char *bodies_directory, const char *output_path) {
    size_t book_count = 0;
    int *book_ids = discover_book_ids(bodies_directory, &book_count);
    InvertedIndex *index = index_create();
    for (size_t position = 0; position < book_count; position++) {
        char body_path[MAX_PATH_LENGTH];
        snprintf(body_path, sizeof(body_path), "%s/%d%s", bodies_directory, book_ids[position], BODY_SUFFIX);
        char *text = read_text_file(body_path);
        TokenList tokens = process_text(text);
        index_add_book(index, book_ids[position], &tokens);
        free_token_list(&tokens);
        free(text);
    }
    index_save(index, output_path);
    printf("Index contains %zu unique terms\n", index->count);
    index_destroy(index);
    free(book_ids);
}

static void query_index(const char *index_path, char **terms, size_t term_count) {
    InvertedIndex *index = index_load(index_path);
    for (size_t position = 0; position < term_count; position++) {
        size_t postings_count = 0;
        const int *postings = index_query(index, terms[position], &postings_count);
        printf("%s: [", terms[position]);
        for (size_t book_index = 0; book_index < postings_count; book_index++) {
            printf(book_index == 0 ? "%d" : ", %d", postings[book_index]);
        }
        printf("]\n");
    }
    index_destroy(index);
}

static void print_usage(void) {
    fprintf(stderr, "Usage: index_c build <bodies_dir> <output_json>\n");
    fprintf(stderr, "       index_c query <index_json> <term>...\n");
}

int main(int argc, char **argv) {
    if (argc == 4 && strcmp(argv[1], "build") == 0) {
        build_index(argv[2], argv[3]);
    } else if (argc >= 4 && strcmp(argv[1], "query") == 0) {
        query_index(argv[2], argv + 3, (size_t)(argc - 3));
    } else {
        print_usage();
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
