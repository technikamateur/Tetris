#include "ctmanage.h"
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>

static size_t size = 2;
static size_t next_free = 0;
static size_t head = 0;
static pthread_t *thread_array = NULL;

void CTM_Add_Thread(pthread_t thread_handle) {
    printf("New thread spawned: %lu\n", thread_handle);
    // create array if first element
    if(thread_array == NULL) {
        thread_array = (pthread_t *) malloc(size * sizeof(pthread_t));
    }
    if(size == next_free) {
        // we reached end of array -> realloc
        size = 2 * size;
        thread_array = (pthread_t *) realloc(thread_array, size * sizeof(pthread_t));
    }
    thread_array[next_free] = thread_handle;
    next_free++;
    return;
}

pthread_t CTM_Fetch_Thread(void) {
    // No element or head is at next_free position
    if(head == next_free) {
        head = 0;
        return 0;
    } else {
        head++;
        return thread_array[head-1];
    }
}
