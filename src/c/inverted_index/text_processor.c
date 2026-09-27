#include "text_processor.h"

#include "util.h"

#include <stdlib.h>
#include <string.h>

static const char *const ROMAN_NUMERALS[] = {
    "c", "i", "ii", "iii", "iv", "ix", "l", "lx", "lxx", "lxxx", "v",
    "vi", "vii", "viii", "x", "xc", "xi", "xii", "xiii", "xiv", "xix",
    "xl", "xv", "xvi", "xvii", "xviii", "xx", "xxi", "xxii", "xxiii",
    "xxiv", "xxix", "xxv", "xxvi", "xxvii", "xxviii", "xxx"
};

static const char *const STOP_WORDS[] = {
    "a", "about", "after", "again", "all", "also", "an", "and", "are",
    "as", "at", "back", "be", "been", "before", "being", "between",
    "both", "but", "by", "can", "could", "did", "do", "does", "each",
    "even", "every", "few", "for", "from", "had", "has", "have", "he",
    "her", "here", "his", "how", "i", "if", "in", "into", "is", "it",
    "its", "just", "many", "may", "me", "might", "more", "most", "much",
    "my", "new", "no", "not", "now", "of", "off", "on", "one", "only",
    "or", "other", "our", "out", "over", "own", "same", "shall", "she",
    "should", "so", "some", "still", "such", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "those",
    "three", "through", "to", "too", "two", "under", "up", "very", "was",
    "we", "well", "were", "when", "where", "why", "will", "with", "would",
    "you", "your"
};

#define ROMAN_NUMERAL_COUNT (sizeof(ROMAN_NUMERALS) / sizeof(ROMAN_NUMERALS[0]))
#define STOP_WORD_COUNT (sizeof(STOP_WORDS) / sizeof(STOP_WORDS[0]))
#define FILTER_TABLE_SIZE 512

static const char *filter_table[FILTER_TABLE_SIZE];
static int filter_ready = 0;

static void filter_insert(const char *word) {
    size_t slot = (size_t)(fnv1a_hash(word) & (FILTER_TABLE_SIZE - 1));
    while (filter_table[slot] != NULL) {
        if (strcmp(filter_table[slot], word) == 0) {
            return;
        }
        slot = (slot + 1) & (FILTER_TABLE_SIZE - 1);
    }
    filter_table[slot] = word;
}

static void filter_init(void) {
    if (filter_ready) {
        return;
    }
    for (size_t index = 0; index < ROMAN_NUMERAL_COUNT; index++) {
        filter_insert(ROMAN_NUMERALS[index]);
    }
    for (size_t index = 0; index < STOP_WORD_COUNT; index++) {
        filter_insert(STOP_WORDS[index]);
    }
    filter_ready = 1;
}

static int should_keep(const char *token) {
    if (strlen(token) <= 1) {
        return 0;
    }
    size_t slot = (size_t)(fnv1a_hash(token) & (FILTER_TABLE_SIZE - 1));
    while (filter_table[slot] != NULL) {
        if (strcmp(filter_table[slot], token) == 0) {
            return 0;
        }
        slot = (slot + 1) & (FILTER_TABLE_SIZE - 1);
    }
    return 1;
}

static void token_list_append(TokenList *tokens, const char *token) {
    if (tokens->count == tokens->capacity) {
        tokens->capacity = tokens->capacity == 0 ? 64 : tokens->capacity * 2;
        tokens->items = realloc(tokens->items, tokens->capacity * sizeof(char *));
        if (tokens->items == NULL) {
            die("out of memory");
        }
    }
    tokens->items[tokens->count++] = xstrdup(token);
}

static void append_run_if_kept(TokenList *tokens, char *run, size_t run_length) {
    run[run_length] = '\0';
    if (should_keep(run)) {
        token_list_append(tokens, run);
    }
}

static char *grow_run_buffer(char *run, size_t *capacity) {
    *capacity *= 2;
    run = realloc(run, *capacity);
    if (run == NULL) {
        die("out of memory");
    }
    return run;
}

TokenList process_text(const char *text) {
    filter_init();
    TokenList tokens = {0};
    size_t run_length = 0;
    size_t run_capacity = 32;
    char *run = malloc(run_capacity);
    if (run == NULL) {
        die("out of memory");
    }
    for (const unsigned char *cursor = (const unsigned char *)text; *cursor != '\0'; cursor++) {
        unsigned char byte = *cursor;
        if (byte >= 'A' && byte <= 'Z') {
            byte = (unsigned char)(byte + 32);
        }
        if (byte >= 'a' && byte <= 'z') {
            if (run_length + 1 >= run_capacity) {
                run = grow_run_buffer(run, &run_capacity);
            }
            run[run_length++] = (char)byte;
        } else if (run_length > 0) {
            append_run_if_kept(&tokens, run, run_length);
            run_length = 0;
        }
    }
    if (run_length > 0) {
        append_run_if_kept(&tokens, run, run_length);
    }
    free(run);
    return tokens;
}

void free_token_list(TokenList *tokens) {
    for (size_t index = 0; index < tokens->count; index++) {
        free(tokens->items[index]);
    }
    free(tokens->items);
    tokens->items = NULL;
    tokens->count = 0;
    tokens->capacity = 0;
}
