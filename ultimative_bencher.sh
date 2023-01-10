#!/bin/bash

benchmarks=("IS" "FT" "EP" "CG" "MG")
classes=("B")
cores=("4" "1")
threads=("1")

# compile if needed
if [[ ! -d "bin" ]]; then
    mkdir bin
    for bench in ${benchmarks[@]}; do
        for class in ${classes[@]}; do
            make $bench CLASS=$class
        done
    done
fi

if [[ ! -d "results" ]]; then
    mkdir results
fi

currentDate=`date +"%Y-%m-%d-%H-%M-%S"`
mkdir ./results/$currentDate

perfParanoia=`cat /proc/sys/kernel/perf_event_paranoid`
if [[ perfParanoia -ne "-1" ]]; then
    echo "Perf is too paranoid."
    exit 1
fi

export WAIT_FOR_PIPE=1

for f in ./bin/*.x; do
    bname=./results/$currentDate/${f##*/}
    for core in ${cores[@]}; do
        /usr/bin/time -f %U,%S,%e perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>>$bname#$core,4.txt &
        while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
            sleep 1
        done
        echo $core > set_cores.pipe

        while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
            sleep 1
        done
    done

    for thr in ${threads[@]}; do
        /usr/bin/time -f %U,%S,%e perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>$bname#4,$thr.txt &
        while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
            sleep 1
        done
        echo $thr > set_threads.pipe

        while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
            sleep 1
        done
    done
done
