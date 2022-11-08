#define _GNU_SOURCE

#include <stdio.h>

// dlsym shit
#include <link.h>
#include <string.h>
#include <dlfcn.h>

// named pipe
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>


static uint8_t OMP_APP = 0;
static const char *PIPE_PATH = "test.pipe";
static int num_threads = 4;

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

static void create_pipe(void){
    mkfifo(PIPE_PATH, 0666);
    int fd_extern = open(PIPE_PATH, O_RDONLY);
    char buf[256];
    read(fd_extern, buf, 1);
    printf("Okay. We are gonna use %c threads.\n", buf[0]);
    num_threads = buf[0] - '0';
    close(fd_extern);
    unlink(PIPE_PATH);
    return;
}

static void main(void) __attribute__((constructor));

void main(void) {
    dl_iterate_phdr(omp_checker, NULL);
    if (OMP_APP) {
        printf("App uses OMP!\n");
        create_pipe();
        set_threads(num_threads);
    } else {
        printf("App does not use OMP!\n");
    }
    printf("--------\n");
    return;
}
