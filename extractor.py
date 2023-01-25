import os
import glob
import matplotlib.pyplot as plt

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


for file in os.scandir(result_dir):
    fname = os.path.splitext(file.name)[0]  # remove file extension
    key, constellation = fname.split(delimiter)
    cores, threads = constellation.split(",")
    bench = Bench(int(cores), int(threads))
    bench_dict.setdefault(key, []).append(bench)
    bench.populate_from_file(file.path)


for name, benchs in bench_dict.items():
    print("Benchmark {}".format(name))
    plt.style.use('ggplot')
    fig, ax = plt.subplots()
    x_axes, y_user, y_sys, y_exe = (list() for i in range(4))
    for b in benchs:
        x_axes.append(str(b.cores) + "/" + str(b.threads))
        y_user.append(b.user[0])
        y_sys.append(b.sys[0])
        y_exe.append(b.execution[0])
    ax.set_ylabel("time in seconds")
    ax.set_xlabel("Cores/Threads")
    ax.plot(x_axes, y_user, 'o-', label="user time")
    ax.plot(x_axes, y_sys, 'o-', label="sys time")
    ax.plot(x_axes, y_exe, 'o-', label="exe time")
    plt.legend()
    fig.savefig("pics/{}.svg".format(name))
    plt.close()
