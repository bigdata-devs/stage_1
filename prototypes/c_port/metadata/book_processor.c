#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <pcre2posix.h>
#include <time.h>
#include <sys/stat.h>
#include <direct.h>
#include "metadata.h"

struct MemoryStruct {
    char *memory;
    size_t size;
};

static size_t WriteMemoryCallback(void *contents, size_t size, size_t nmemb, void *userp) {
    size_t realsize = size * nmemb;
    struct MemoryStruct *mem = (struct MemoryStruct *)userp;
    char *ptr = realloc(mem->memory, mem->size + realsize + 1);
    if (!ptr) return 0;
    mem->memory = ptr;
    memcpy(&(mem->memory[mem->size]), contents, realsize);
    mem->size += realsize;
    mem->memory[mem->size] = 0;
    return realsize;
}

void extract_metadata(const char *text, const char *pattern, char *output, size_t max_len) {
    regex_t regex;
    regmatch_t matches[2]; 
    strcpy(output, "Unknown"); 

    if (regcomp(&regex, pattern, REG_EXTENDED | REG_ICASE) == 0) {
        if (regexec(&regex, text, 2, matches, 0) == 0) {
            int len = matches[1].rm_eo - matches[1].rm_so;
            if (len > 0 && len < max_len) {
                strncpy(output, text + matches[1].rm_so, len);
                output[len] = '\0';
                
                char *cr = strchr(output, '\r');
                if (cr) *cr = '\0';
            }
        }
        regfree(&regex);
    }
}

BookMetadata process_book(int book_id, const char *output_dir, StorageBackend *db_backend) {
    BookMetadata metadata = {0};
    metadata.book_id = book_id;

    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    snprintf(metadata.capture_date, sizeof(metadata.capture_date), "%d-%02d-%02d %02d:%02d:%02d",
             tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);

    CURL *curl_handle;
    CURLcode res;
    struct MemoryStruct chunk;
    chunk.memory = malloc(1);
    chunk.size = 0;

    curl_global_init(CURL_GLOBAL_ALL);
    curl_handle = curl_easy_init();
    
    char url[256];
    snprintf(url, sizeof(url), "https://www.gutenberg.org/cache/epub/%d/pg%d.txt", book_id, book_id);

    curl_easy_setopt(curl_handle, CURLOPT_URL, url);
    curl_easy_setopt(curl_handle, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl_handle, CURLOPT_WRITEFUNCTION, WriteMemoryCallback);
    curl_easy_setopt(curl_handle, CURLOPT_WRITEDATA, (void *)&chunk);

    res = curl_easy_perform(curl_handle);

    if(res == CURLE_OK) {
        const char *START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK";
        const char *END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK";
        
        char *start_ptr = strstr(chunk.memory, START_MARKER);
        char *end_ptr = strstr(chunk.memory, END_MARKER);

        if (start_ptr && end_ptr) {
            extract_metadata(chunk.memory, "Title:[ \t]*([^\n]+)", metadata.title, sizeof(metadata.title));
            extract_metadata(chunk.memory, "Author:[ \t]*([^\n]+)", metadata.author, sizeof(metadata.author));
            extract_metadata(chunk.memory, "Language:[ \t]*([^\n]+)", metadata.language, sizeof(metadata.language));
            
            db_backend->save(db_backend, &metadata);

            _mkdir(output_dir); 

            char header_path[512];
            snprintf(header_path, sizeof(header_path), "%s/%d_header.txt", output_dir, book_id);
            FILE *h_file = fopen(header_path, "wb");
            if (h_file) {
                fwrite(chunk.memory, 1, start_ptr - chunk.memory, h_file);
                fclose(h_file);
            }

            char body_path[512];
            snprintf(body_path, sizeof(body_path), "%s/%d_body.txt", output_dir, book_id);
            FILE *b_file = fopen(body_path, "wb");
            if (b_file) {
                fwrite(start_ptr, 1, end_ptr - start_ptr, b_file);
                fclose(b_file);
            }
            
            printf("Text files successfully generated in: %s\n", output_dir);
        } else {
            printf("Markers not found in the text.\n");
        }
    } else {
        fprintf(stderr, "Download error: %s\n", curl_easy_strerror(res));
    }

    curl_easy_cleanup(curl_handle);
    free(chunk.memory);
    curl_global_cleanup();

    return metadata;
}