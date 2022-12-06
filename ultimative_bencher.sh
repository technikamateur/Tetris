#!/bin/bash

benchmarks=("IS" "FT")
classes=("B" "C")

for bench in ${benchmarks[@]}; do
    for class in ${classes[@]}; do
        make $bench CLASS=$class
    done
done

for f in ./bin/*.x; do
    LD_PRELOAD=./is_it_openmp.so $f
done
