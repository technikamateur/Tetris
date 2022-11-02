#define _GNU_SOURCE
#include <link.h>
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

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

static void dl_iter(void) __attribute__((constructor));

void dl_iter(void) {
    dl_iterate_phdr(omp_checker, NULL);
    if (OMP_APP) {
        printf("App uses OMP!\n");
        set_threads(4);
    } else {
        printf("App does not use OMP!\n");
    }
    printf("--------\n");
    return;
}
