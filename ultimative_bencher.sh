#!/bin/bash

benchmarks=("IS" "FT")
classes=("B" "C")

for bench in ${benchmarks[@]}; do
    for class in ${classes[@]}; do
        make $bench CLASS=$class
    done
done

for f in ./bin/*.x; do
    /usr/bin/time -f %U,%S,%e -o $f.time perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>$f.txt
done
