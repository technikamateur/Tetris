#!/bin/bash

benchmarks=("IS" "FT" "EP" "CG" "MG")
classes=("A")
cores=("1" "4")
threads=("1")

for bench in ${benchmarks[@]}; do
    for class in ${classes[@]}; do
        make $bench CLASS=$class
    done
done

for f in ./bin/*.x; do
    for core in ${cores[@]}; do
        /usr/bin/time -f %U,%S,%e -o $f.CORES$core.time perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>$f.CORES$core.txt &
        while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
            sleep 0.1
        done
        echo $core > set_cores.pipe

        while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
            sleep 1
        done
    done

    for thr in ${threads[@]}; do
        /usr/bin/time -f %U,%S,%e -o $f.THR$thr.time perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>$f.THR$thr.txt &
        while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
            sleep 0.5
        done
        echo $thr > set_threads.pipe

        while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
            sleep 1
        done
    done
done
