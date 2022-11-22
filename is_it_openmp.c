#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <stdatomic.h>

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

// cpu affinity
#include <sched.h>


#define MAX_EVENTS 2
#define READ_SIZE 10
static uint8_t OMP_APP = 0;
static const char *THREAD_PIPE = "set_threads.pipe";
static const char *CORE_PIPE = "set_cores.pipe";
static int internal_fds[2];
_Atomic static unsigned requested_thread_num = 0;


void (*gomp_parallel_enter)(void (*fn) (void *), void *data, unsigned num_threads, unsigned int flags) = NULL;

struct thread_args {
    int int_pipe_fd;
};

static int omp_checker(struct dl_phdr_info *i, size_t size, void *data) {
    if (strstr(i->dlpi_name, "libomp") != NULL) {
        OMP_APP = 1;
        printf("App uses OMP!\n");
        return 1;
    }
    if (strstr(i->dlpi_name, "libgomp") != NULL) {
        OMP_APP = 1;
        printf("App uses GOMP!\n");
        gomp_parallel_enter = dlsym(RTLD_NEXT, "GOMP_parallel");
        return 1;
    }
    return 0;
}

void GOMP_parallel (void (*fn) (void *), void *data, unsigned num_threads, unsigned int flags) {
    gomp_parallel_enter(fn, data, requested_thread_num, flags);
    return;
}

static void limit_cpus(unsigned cpu_limit) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(0, &cpuset);
    if (sched_setaffinity(getpid(), sizeof(cpuset), &cpuset) == -1) {
        perror("Failed to set affinity\n");
    }
    return;
}

static void *listening(void *arg){
    // get thread args for internal pipe
    struct thread_args* targs = arg;
    int internal_pipe = targs->int_pipe_fd;

    // create named pipe for thread & core com
    mkfifo(THREAD_PIPE, 0666);
    mkfifo(CORE_PIPE, 0666);
    int fd_threads = open(THREAD_PIPE, O_RDWR | O_NONBLOCK);
    int fd_cores = open(CORE_PIPE, O_RDWR | O_NONBLOCK);

    // epoll
    struct epoll_event event, events[MAX_EVENTS];
    // listen on incomming data. Hangup is always watched.
    event.events = EPOLLIN;
    int epoll_fd = epoll_create1(0);
    if (epoll_fd == -1) {
        perror("Failed to create epoll fd\n");
    }

    // add fd's to epoll
    event.data.fd = internal_pipe;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, internal_pipe, &event) == -1) {
        perror("Failed to add internal pipe file descriptor to epoll\n");
    }
    event.data.fd = fd_threads;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, fd_threads, &event) == -1) {
        perror("Failed to add external pipe file descriptor to epoll\n");
    }
    event.data.fd = fd_cores;
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, fd_cores, &event) == -1) {
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
            // internal pipe = message from parent
            if (events[i].data.fd == internal_pipe && events[i].events == EPOLLHUP) {
                done = 1;
                break;
            }
            // new thread advice
            if (events[i].data.fd == fd_threads) {
                bytes_read = read(events[i].data.fd, buf, READ_SIZE);
                buf[bytes_read] = '\0';
                printf("Got a new thread advice: %d\n", atoi(buf));
                requested_thread_num = atoi(buf);
            }
            // new core instruction
            if (events[i].data.fd == fd_cores) {
                bytes_read = read(events[i].data.fd, buf, READ_SIZE);
                buf[bytes_read] = '\0';
                printf("Got a new cores advice: %d\n", atoi(buf));
                limit_cpus(0);
            }

        }
    }

    // clean up
    printf("Main thread closed pipe. Exiting normally...\n");
    close(internal_pipe);
    close(fd_threads);
    close(fd_cores);
    close(epoll_fd);
    unlink(THREAD_PIPE);
    unlink(CORE_PIPE);
    return NULL;
}

static int main(void) __attribute__((constructor));
static void finalize(void) __attribute__((destructor));

static pthread_t listener_id;
static struct thread_args listener_args;

int main(void) {
    /* Check for OMP support */
    dl_iterate_phdr(omp_checker, NULL);
    // remove exisiting pipe in case of unclean shutdown
    remove(THREAD_PIPE);
    remove(CORE_PIPE);

    if (OMP_APP) {
        // pipe to child
        pipe(internal_fds);
        // start listener thread
        listener_args.int_pipe_fd = internal_fds[0];
        pthread_create(&listener_id, NULL, listening, &listener_args);
        //close(internal_fds[1]);
        //pthread_join(listener_id, NULL);
    } else {
        printf("App does not use OMP!\n");
    }
    printf("--------\n");
    return 0;
}

static void finalize(void) {
    if (OMP_APP) {
        close(internal_fds[1]);
        pthread_join(listener_id, NULL);
    }
    return;
}
