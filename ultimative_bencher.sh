#!/bin/bash

benchmarks=("IS" "FT" "EP" "CG" "MG")
classes=("B")
cores=("4" "1")
threads=("1")

if [[ ! -d "bin" ]]; then
    mkdir bin
    for bench in ${benchmarks[@]}; do
        for class in ${classes[@]}; do
            make $bench CLASS=$class
        done
    done
fi

currentDate=`date +"%Y-%m-%d-%H-%M-%S"`

if [[ ! -d "results" ]]; then
    mkdir results
fi
mkdir ./results/$currentDate

for f in ./bin/*.x; do
    bname=./results/$currentDate/${f##*/}
    for core in ${cores[@]}; do
        /usr/bin/time -f %U,%S,%e perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>>$bname.CORES$core.txt &
        while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
            sleep 0.1
        done
        echo $core > set_cores.pipe

        while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
            sleep 1
        done
    done

    for thr in ${threads[@]}; do
        /usr/bin/time -f %U,%S,%e perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>$bname.THR$thr.txt &
        while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
            sleep 0.1
        done
        echo $thr > set_threads.pipe

        while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
            sleep 1
        done
    done
done
