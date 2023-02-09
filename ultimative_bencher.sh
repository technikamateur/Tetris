#!/bin/bash

### Adjust the following
benchmarks=("IS" "FT" "EP" "CG" "MG")
classes=("B" "C")
cores=("8" "4" "2" "1")
threads=("8" "4" "2" "1")
selection=("0" "All" "1" "Normal" "2" "Half")
###

# We all love colors
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

### Here begins program
function normal_bench() {
    export WAIT_FOR_PIPE=2
    for f in ./bin/*.x; do
        bname=./results/$currentDate/${f##*/}
        for i in {1..5}; do
            for core in ${cores[@]}; do
                for thr in ${threads[@]}; do
                    perf stat --field-separator , -e duration_time,energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>>$bname#$core,$thr.txt | tee -a $bname.log &
                    while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
                        sleep 0.1
                    done

                    echo $core > set_cores.pipe
                    echo $thr > set_threads.pipe

                    while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
                        sleep 1
                    done
                done
            done
        done
    done
    unset WAIT_FOR_PIPE
}

function half_bench() {
    export WAIT_FOR_PIPE=2
    thr="1"
    for f in ./bin/*.x; do
        bname=./results/$currentDate/${f##*/}_half
        for core in ${cores[@]}; do
            if [[ $core -eq "1" ]]; then
                continue
            fi
            # measure exec time
            /usr/bin/time -f %e $f 2> /tmp/exec_time
            while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
                sleep 1
            done
            echo $core > set_cores.pipe
            echo $core > set_threads.pipe
            while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
                sleep 1
            done
            # calculate half
            duration=$(</tmp/exec_time)
            sleep_duration=$(bc -l <<<"scale=1; ${duration}/2")
            echo "#${sleep_duration}" > $bname#$core,$thr.txt
            # bench and switch threads after half of time
            for i in {1..5}; do
                perf stat --field-separator , -e duration_time,energy-pkg,energy-cores env LD_PRELOAD=./is_it_openmp.so $f 2>>$bname#$core,$thr.txt | tee -a $bname.log &
                while [ ! -p set_cores.pipe -a ! -p set_threads.pipe ]; do
                    sleep 0.1
                done
                echo $core > set_cores.pipe
                echo $core > set_threads.pipe
                sleep $sleep_duration
                echo $core > set_cores.pipe
                echo $thr > set_threads.pipe

                while [ -p set_cores.pipe -a -p set_threads.pipe ]; do
                    sleep 1
                done
            done
        done
    done
    unset WAIT_FOR_PIPE
}

function compile() {
    mkdir bin
    for bench in ${benchmarks[@]}; do
        for class in ${classes[@]}; do
            make $bench CLASS=$class
        done
    done
}

# experimental check
expected_files=$((${#benchmarks[@]}*${#classes[@]}))
counted_files=`ls -1q bin | wc -l`
me=`basename "$0"`

# compile if needed
if [[ ! -d "bin" ]]; then
    echo -e "${BLUE}Info:${NC} bin not found. Compiling..."
    compile
else
    if [[ $expected_files -ne $counted_files ]]; then
        echo -e "${YELLOW}Warning:${NC} You specified $expected_files benchmarks in $me, but I found only $counted_files."
        read -p "Shall I compile that for you? [Y/n] " yn
        if [[ $yn =~ ^[Nn]$ ]]; then
            echo "Okay. Bye Bye."
            exit 2
        else
            compile
        fi
    else
        echo -e "${BLUE}Info:${NC} bin already exists. Skipping compile step."
    fi
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

perfParanoia=$(</proc/sys/kernel/perf_event_paranoid)
if [[ perfParanoia -ne "-1" ]]; then
    echo -e "${RED}Perf is too paranoid.${NC}"
    exit 1
fi

selection=$(dialog --title "Benchmark Selection" --menu "Select a Benchmark to run" 24 40 5 "${selection[@]}" 3>&2 2>&1 1>&3)
case ${selection} in
    0)
        normal_bench
        half_bench;;
    1)
        normal_bench;;
    2)
        half_bench;;
    *)
        echo "Okay. Bye Bye."
esac
