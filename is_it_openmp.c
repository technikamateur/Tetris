#define _GNU_SOURCE
#include <link.h>
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

// for sockets
#include <sys/socket.h>
#include <sys/un.h>
#define SOCK_PATH  "test.sock"

// for unlink
#include <unistd.h>

static uint8_t OMP_APP = 0;

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

static void create_socket(void){
    struct sockaddr_un addr;

    // Create a UNIX domain socket
    int sock_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    printf("Server socket fd = %d\n", sock_fd);
    if (sock_fd == -1) {
        printf("socket fd could not be created!\n");
    }

    // Clearing path of future socket
    unlink(SOCK_PATH);

    // Zero out the address, and set family and path
    memset(&addr, 0, sizeof(struct sockaddr_un));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCK_PATH, sizeof(addr.sun_path) - 1);

    // Bind the socket to the address
    if (bind(sock_fd, (struct sockaddr *) &addr, sizeof(struct sockaddr_un)) == -1) {
        printf("Binding failed!\n");
    }

    // Set socket to listen mode
    if (listen(sock_fd, 1) == -1) {
        printf("Listen failed!\n");
    }

    char buf[256];
    ssize_t n = read(sock_fd, buf, 1);
    printf("LOL%cLOL\n", buf[0]);
    close(sock_fd);
    printf("Socket closed.\n");
    return;
}

static void main(void) __attribute__((constructor));

void main(void) {
    dl_iterate_phdr(omp_checker, NULL);
    if (OMP_APP) {
        printf("App uses OMP!\n");
        set_threads(4);
    } else {
        printf("App does not use OMP!\n");
    }
    printf("--------\n");
    create_socket();
    return;
}
