#define _GNU_SOURCE

#include <stdio.h>

// dlsym & more
#include <link.h>
#include <string.h>
#include <dlfcn.h>
#include <stdlib.h>

// named pipe
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

// pthread
#include <pthread.h>

// epoll
#include <sys/epoll.h>

#define MAX_EVENTS 2
static uint8_t OMP_APP = 0;
static const char *PIPE_PATH = "test.pipe";

static int omp_checker(struct dl_phdr_info *i, size_t size, void *data) {
    if ((strstr(i->dlpi_name, "libomp") != NULL) || (strstr(i->dlpi_name, "libgomp") != NULL)) {
        OMP_APP = 1;
        return 1;
    }
    return 0;
}

static void set_threads(int num){
    void *(*omp_set_threads)(int) = NULL;
    omp_set_threads = dlsym(RTLD_NEXT, "omp_set_num_threads");
    omp_set_threads(num);
    return;
}

static void *create_pipe(void *arg){
    // dereference internal pipe
    int internal_pipe = *((int *) arg);
    fprintf(stderr, "Intpipe:%d\n", internal_pipe);
    // create named pipe for external com
    mkfifo(PIPE_PATH, 0666);
    int fd_extern = open(PIPE_PATH, O_RDONLY | O_NONBLOCK);
    fprintf(stderr, "Intpipe:%d\n", fd_extern);
    // epoll
    struct epoll_event event, events[MAX_EVENTS];
    event.events = EPOLLIN;
    int epoll_fd = epoll_create(0);
    int event_count;
    char buf[2];

    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, internal_pipe, &event) || epoll_ctl(epoll_fd, EPOLL_CTL_ADD, fd_extern, &event)) {
        printf("Failed to add file descriptor to epoll\n");
        close(epoll_fd);
    }
    fprintf(stderr, "LOLOLOLOL%d", epoll_fd);
        {
        event_count = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        printf("%d ready events\n", event_count);
        for (int i = 0; i < event_count; i++) {
            printf("Reading file descriptor '%d' -- ", events[i].data.fd);
            read(events[i].data.fd, buf, 1);
            printf("Okay. We are gonna use %c threads.\n", buf[0]);
        }
    }



    read(fd_extern, buf, 1);
    printf("Okay. We are gonna use %c threads.\n", buf[0]);
    set_threads(atoi(&buf[0]));
    // clean up
    close(fd_extern);
    close(epoll_fd);
    unlink(PIPE_PATH);
}

static void main(void) __attribute__((constructor));

void main(void) {
    pthread_t listener_id;
    dl_iterate_phdr(omp_checker, NULL);
    if (OMP_APP) {
        printf("App uses OMP!\n");
        // pipe to child
        int internal_fds[2];
        pipe(internal_fds);
        // start listener thread
        pthread_create(&listener_id, NULL, create_pipe, &internal_fds[0]);
        pthread_join(listener_id, NULL);
    } else {
        printf("App does not use OMP!\n");
    }
    printf("--------\n");
    return;
}
