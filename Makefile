CC = gcc
RM = rm -r
SRC = is_it_openmp.c ctmanage.c
OBJ = $(SRC:.c=.o)

all: gof is_it_openmp.so

gof: gof_parallel.c Makefile
	$(CC) -fopenmp $< -o $@

is_it_openmp.so: $(OBJ)
	$(CC) -shared $^ -o $@

is_it_openmp.o: is_it_openmp.c Makefile
	$(CC) -c -fPIC $< -o $@

ctmanage.o: ctmanage.c Makefile
	$(CC) -c -fPIC $< -o $@

.PHONY: clean

clean:
	$(RM) gof is_it_openmp.so $(OBJ)
