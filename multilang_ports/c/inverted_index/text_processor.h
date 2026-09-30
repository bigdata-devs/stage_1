#ifndef TEXT_PROCESSOR_H
#define TEXT_PROCESSOR_H

#include <stddef.h>

typedef struct {
    char **items;
    size_t count;
    size_t capacity;
} TokenList;

TokenList process_text(const char *text);
void free_token_list(TokenList *tokens);

#endif
