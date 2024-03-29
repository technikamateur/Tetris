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

#include <errno.h>

#define MAX_EVENTS 2
#define READ_SIZE 10

static uint8_t OMP_APP = 0;
static uint8_t HALT_STOP = 0;

// Setting and managing threads
typedef struct ThreadInfo_s {
    pthread_t* thread_handle;
    pid_t tid;
    void* (*func)(void*);
    void* arg;
    uint8_t dead;
    struct ThreadInfo_s *next;
} ThreadInfo;
static ThreadInfo *first = NULL;
static ThreadInfo *head = NULL;
pthread_mutex_t remove_mutex = PTHREAD_MUTEX_INITIALIZER;

// listener thread
static const char *THREAD_PIPE = "set_threads.pipe";
static const char *CORE_PIPE = "set_cores.pipe";
static int internal_fds[2];
_Atomic static unsigned requested_thread_num = 0;
struct thread_args {
    int int_pipe_fd;
};

// function pointers
void (*gomp_parallel_enter)(void (*fn) (void *), void *data, unsigned num_threads, unsigned int flags) = NULL;
int (*real_pthread_create)(pthread_t *restrict thread, const pthread_attr_t *restrict attr,
                          void *(*start_routine)(void *), void *restrict arg) = NULL;

void (*real_pthread_exit)(void *retval) __attribute__((noreturn));

static int omp_checker(struct dl_phdr_info *i, size_t size, void *data) {
    if (strstr(i->dlpi_name, "libomp") != NULL) {
        OMP_APP = 1;
        printf("App uses OMP!\nTHIS IS NOT TESTED!\n");
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

void GOMP_parallel (void (*fn) (void *), void *data, unsigned /*num_threads*/, unsigned int flags) {
    gomp_parallel_enter(fn, data, requested_thread_num, flags);
    return;
}

void remove_by_tid(pid_t tid) {
    // Grab a lock. It might be called by multiple threads
    pthread_mutex_lock(&remove_mutex);
    ThreadInfo *dead_thread = NULL;
    // we don't need to check main thread
    ThreadInfo *list_walker = first->next;
    while (list_walker->next != NULL) {
        if(list_walker->next->tid == tid) {
            dead_thread = list_walker->next;
            list_walker->next = dead_thread->next;
            free(dead_thread);
            break;
        }
        list_walker = list_walker->next;
    }
    if (dead_thread == NULL) {
        printf("Could't find thread with tid %d. Don't worry - it's just a waste of memory.\n", tid);
    }
    // we must take care about the head
    if (list_walker->next == NULL) {
        head = list_walker;
    }
    pthread_mutex_unlock(&remove_mutex);
    return;
}

void *thread_wrapper_func(void *arg) {
    // might be called by multiple threads
    ThreadInfo *thrd = arg;
    // stor tid
    thrd->tid = gettid();
    printf("Thread with tid %d spawned.\n", thrd->tid);
    // start function
    thrd->func(thrd->arg);
    // function ended - cleanup
    thrd->dead = 1;
    printf("Thread with tid %d returned.\n", thrd->tid);
    remove_by_tid(thrd->tid);
    return NULL;
}

int pthread_create(pthread_t *restrict thread, const pthread_attr_t *restrict attr,
                   void *(*start_routine)(void *), void *restrict arg) {
    if (OMP_APP) {
        // Grab a lock. It might be called by multiple threads
        pthread_mutex_lock(&remove_mutex);
        // creating thread structure
        head->next = (ThreadInfo *) malloc(sizeof(ThreadInfo));
        head = head->next;
        head->thread_handle = thread;
        head->func = start_routine;
        head->arg = arg;
        head->dead = 0;
        head->next = NULL;
        pthread_mutex_unlock(&remove_mutex);
        // use my function to control the pthread
        return real_pthread_create(thread, attr, thread_wrapper_func, head);
    } else {
        return real_pthread_create(thread, attr, start_routine, arg);
    }
}

void pthread_exit(void *retval) {
    // might be called by multiple threads
    pid_t tid = gettid();
    printf("Thread with tid %d exited.\n", tid);
    remove_by_tid(tid);
    real_pthread_exit(retval);
}

static void limit_cpus(unsigned cpu_limit) {
    unsigned i = 0;
    ThreadInfo *list_walker = first;
    // setting cpus
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    while (i < cpu_limit) {
        CPU_SET(i, &cpuset);
        i++;
    }
    i = 0;
    while (list_walker != NULL) {
        if (list_walker->dead) {
            printf("Found a dead thread. Num: %d, TID: %d. Skipping it.\n", i, list_walker->tid);
            list_walker = list_walker->next;
            i++;
            continue;
        }
        if (sched_setaffinity(list_walker->tid, sizeof(cpuset), &cpuset) == -1) {
            printf("Failed to set affinity. Num: %d, TID: %d, Errno: %d\n", i, list_walker->tid, errno);
        }
        if (list_walker->tid == 0) {
            printf("Discovered a thread with tid %d. His num: %d. This seems to be strange.\n", list_walker->tid, i);
        }
        list_walker = list_walker->next;
        i++;
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
                limit_cpus(atoi(buf));
            }
            if (HALT_STOP) {
                HALT_STOP--;
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

static int startup(void) __attribute__((constructor));
static void finalize(void) __attribute__((destructor));

static pthread_t listener_id;
static struct thread_args listener_args;

int startup(void) {
    // overwrite pthread_create and exit
    real_pthread_create = dlsym(RTLD_NEXT,"pthread_create");
    real_pthread_exit = dlsym(RTLD_NEXT,"pthread_exit");
    /* Check for OMP support */
    dl_iterate_phdr(omp_checker, NULL);
    // remove exisiting pipe in case of unclean shutdown
    remove(THREAD_PIPE);
    remove(CORE_PIPE);

    if (OMP_APP) {
        char *wfp = getenv("WAIT_FOR_PIPE");
        if (wfp != NULL) {
            HALT_STOP = atoi(wfp);
            printf("Waiting for thread/core advice.\n");
        }
        // pipe to child
        pipe(internal_fds);
        // add main thread to thread list
        first = (ThreadInfo *) malloc(sizeof(ThreadInfo));
        head = first;
        head->tid = gettid();
        head->dead = 0;
        head->next = 0;
        printf("MAIN Thread with tid %d added.\n", head->tid);
        // start listener thread
        listener_args.int_pipe_fd = internal_fds[0];
        real_pthread_create(&listener_id, NULL, listening, &listener_args);
    } else {
        printf("App does not use OMP!\n");
    }
    while (HALT_STOP > 0) {
        sleep(0.1);
    }
    printf("--------\n");
    return 0;
}

static void finalize(void) {
    if (OMP_APP) {
        close(internal_fds[1]);
        pthread_join(listener_id, NULL);
        free(first);
    }
    return;
}
