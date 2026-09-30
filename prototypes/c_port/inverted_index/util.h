#ifndef UTIL_H
#define UTIL_H

#include <stddef.h>
#include <stdint.h>

void die(const char *message);
void die_io(const char *context);
uint64_t fnv1a_hash(const char *text);
char *xstrdup(const char *text);
char *read_text_file(const char *path);

#endif
