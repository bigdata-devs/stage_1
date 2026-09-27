#include "util.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void die(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(EXIT_FAILURE);
}

void die_io(const char *context) {
    fprintf(stderr, "%s: %s\n", context, strerror(errno));
    exit(EXIT_FAILURE);
}

uint64_t fnv1a_hash(const char *text) {
    uint64_t hash = 1469598103934665603ULL;
    while (*text != '\0') {
        hash ^= (unsigned char)*text++;
        hash *= 1099511628211ULL;
    }
    return hash;
}

char *xstrdup(const char *text) {
    size_t length = strlen(text);
    char *copy = malloc(length + 1);
    if (copy == NULL) {
        die("out of memory");
    }
    memcpy(copy, text, length + 1);
    return copy;
}

char *read_text_file(const char *path) {
    FILE *stream = fopen(path, "rb");
    if (stream == NULL) {
        die_io(path);
    }
    if (fseek(stream, 0, SEEK_END) != 0) {
        die_io(path);
    }
    long size = ftell(stream);
    if (size < 0) {
        die_io(path);
    }
    rewind(stream);
    char *content = malloc((size_t)size + 1);
    if (content == NULL) {
        die("out of memory");
    }
    if (fread(content, 1, (size_t)size, stream) != (size_t)size) {
        die_io(path);
    }
    content[size] = '\0';
    fclose(stream);
    return content;
}
