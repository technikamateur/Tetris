#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>

// dlsym
#include <link.h>
#include <string.h>
#include <dlfcn.h>

// named pipe
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

// pthread
#include <pthread.h>

// epoll
#include <sys/epoll.h>

#define MAX_EVENTS 2
#define READ_SIZE 10
static uint8_t OMP_APP = 0;
static const char *PIPE_PATH = "test.pipe";

struct thread_args {
    int int_pipe_fd;
};

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
    // get thread args for internal pipe
    struct thread_args* targs = arg;
    int internal_pipe = targs->int_pipe_fd;

    // create named pipe for external com
    mkfifo(PIPE_PATH, 0666);
    int fd_extern = open(PIPE_PATH, O_RDWR | O_NONBLOCK);

    // epoll
    struct epoll_event event, events[MAX_EVENTS];
    event.events = EPOLLIN;
    int epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        perror("Failed to create epoll fd\n");
    }

    event.data.fd = internal_pipe;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, internal_pipe, &event) == -1) {
        perror("Failed to add internal pipe file descriptor to epoll\n");
    }

    event.data.fd = fd_extern;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, fd_extern, &event) == -1) {
        perror("Failed to add external pipe file descriptor to epoll\n");
    }

    int event_count;
    char buf[READ_SIZE + 1];
    uint8_t done = 0;
    size_t bytes_read = 0;
    while (!done) {
        event_count = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        if (event_count == -1) {
            perror("epoll_wait failed!\n");
            break;
        }
        for (int i = 0; i < event_count; i++) {
            if (events[i].data.fd == internal_pipe && events[i].events == EPOLLHUP) {
                done = 1;
                printf("Parrent closed pipe, will now exit.\n");
                break;
            }

            bytes_read = read(events[i].data.fd, buf, READ_SIZE);
            buf[bytes_read] = '\0';
            printf("Got a new thread advice: %d\n", atoi(buf));
            set_threads(atoi(buf));
        }
    }

    // clean up
    close(internal_pipe);
    close(fd_extern);
    close(epoll_fd);
    unlink(PIPE_PATH);
    return NULL;
}

static void main(void) __attribute__((constructor));

static pthread_t listener_id;
static struct thread_args listener_args;

void main(void) {

    /* Check for OMP support */
    dl_iterate_phdr(omp_checker, NULL);
    // remove exisiting pipe in case of unclean shutdown
    remove(PIPE_PATH);

    if (OMP_APP) {
        printf("App uses OMP!\n");
        // pipe to child
        int internal_fds[2];
        pipe(internal_fds);

        // start listener thread
        listener_args.int_pipe_fd = internal_fds[0];
        pthread_create(&listener_id, NULL, create_pipe, &listener_args);
        //close(internal_fds[1]);
        //pthread_join(listener_id, NULL);
    } else {
        printf("App does not use OMP!\n");
    }
    printf("--------\n");
    return;
}
