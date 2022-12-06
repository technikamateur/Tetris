#!/bin/bash

benchmarks=("IS" "FT")
classes=("B")

for bench in ${benchmarks[@]}; do
    for class in ${classes[@]}; do
        make $bench CLASS=$class
    done
done

for f in ./bin/*.x; do
    /usr/bin/time -f %U,%S,%e -o $f.time perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>$f.txt &
    while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
        sleep 0.5
    done

    sleep 0.5
    echo 1 > set_cores.pipe

    while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
        sleep 1
    done
done
