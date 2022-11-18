CC = gcc
RM = rm -r

all: gof is_it_openmp.so

gof: gof_parallel.c Makefile
	$(CC) -fopenmp $< -o $@

is_it_openmp.so: is_it_openmp.c Makefile
	$(CC) -shared -fPIC $< -o $@

.PHONY: clean

clean:
	$(RM) gof is_it_openmp.so
