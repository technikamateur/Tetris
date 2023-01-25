import os
import glob
import matplotlib.pyplot as plt
from statistics import fmean

# Setup
result_dir = "./results"
delimiter = "#"

# search for latest results
result_dir = max(glob.glob(os.path.join(result_dir, '*/')), key=os.path.getmtime)
# some generic setup
bench_dict = dict()
# PANDAS?!
#https://matplotlib.org/3.4.3/gallery/ticks_and_spines/multiple_yaxis_with_spines.html

class Bench:
    def __init__(self, cores: int, threads: int):
        self.threads = threads
        self.cores = cores
        self.energy_pkg = list()
        self.energy_cores = list()
        self.user = list()
        self.sys = list()
        self.execution = list()

    def __str__(self):
        return f"{self.cores} Cores, {self.threads} Threads"

    def populate_from_file(self, file_path: str) -> None:
        with open(file_path, "r") as result:
            line = result.readline().rstrip()
            while line:
                energy_pkg = line
                energy_cores = result.readline().rstrip()
                time = result.readline().rstrip()
                self.energy_pkg.append(float(energy_pkg.split(",")[0]))
                self.energy_cores.append(float(energy_cores.split(",")[0]))
                time_split = time.split(",")
                self.user.append(float(time_split[0]))
                self.sys.append(float(time_split[1]))
                self.execution.append(float(time_split[2]))

                # is there more? -> repetitions
                line = result.readline().rstrip()
        return


cnt = 0

for file in os.scandir(result_dir):
    fname = os.path.splitext(file.name)[0]  # remove file extension
    key, constellation = fname.split(delimiter)
    cores, threads = constellation.split(",")
    bench = Bench(int(cores), int(threads))
    bench_dict.setdefault(key, []).append(bench)
    bench.populate_from_file(file.path)
    cnt += 1

print("Found {} result files.".format(cnt))


for name, benchs in bench_dict.items():
    benchs.sort(key=lambda b: (b.cores, b.threads), reverse=True)
    print("Generating plot for {}".format(name))
    plt.style.use('ggplot')
    fig, ax = plt.subplots()
    twin = ax.twinx()
    x_axes, y_user, y_sys, y_exe, y_e_pkg, y_e_core = (list() for i in range(6))
    for b in benchs:
        x_axes.append(str(b.cores) + "/" + str(b.threads))
        y_user.append(fmean(b.user))
        y_sys.append(fmean(b.sys))
        y_exe.append(fmean(b.execution))
        y_e_pkg.append(fmean(b.energy_pkg))
        y_e_core.append(fmean(b.energy_cores))
    ax.set_ylabel("time in seconds")
    ax.set_xlabel("cores/threads")
    twin.set_ylabel("energy in joules")
    l1, = ax.plot(x_axes, y_user, 'o-', label="user time")
    l2, = ax.plot(x_axes, y_sys, 'o-', label="sys time")
    l3, = ax.plot(x_axes, y_exe, 'o-', label="exe time")
    l4, = twin.plot(x_axes, y_e_core, 'D-', label="energy cores", color="C3")
    l5, = twin.plot(x_axes, y_e_pkg, 'D-', label="energy package", color="C4")
    ax.legend(handles=[l1,l2,l3,l4,l5])
    fig.savefig("pics/{}.svg".format(name))
    plt.close()
