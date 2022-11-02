all: gof is_it_openmp.so

gof: gof_parallel.c
	gcc -fopenmp $^ -o $@

is_it_openmp.so: is_it_openmp.c
	gcc -shared -fPIC $^ -o $@
