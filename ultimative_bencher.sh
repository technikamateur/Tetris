#!/bin/bash

### Adjust the following
benchmarks=("IS" "FT" "EP" "CG" "MG")
classes=("A" "B" "C")
cores=("8" "4" "2" "1")
threads=("8" "4" "2" "1")
###

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

if [[ -p set_cores.pipe ]]; then
    rm set_cores.pipe
fi

if [[ -p set_threads.pipe ]]; then
    rm set_threads.pipe
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
    for i in {1..5}; do
        for core in ${cores[@]}; do
            for thr in ${threads[@]}; do
                /usr/bin/time -f %U,%S,%e perf stat --field-separator , -e energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>>$bname#$core,$thr.txt &
                while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
                    sleep 1
                done

                echo $thr > set_cores.pipe
                echo $thr > set_threads.pipe

                while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
                    sleep 1
                done
            done
        done
    done
done
