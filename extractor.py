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
plt.style.use('ggplot')


class Bench:
    def __init__(self, cores: int, threads: int):
        self.threads = threads
        self.cores = cores
        self.energy_pkg = 0
        self.energy_cores = 0
        self.user = 0
        self.sys = 0
        self.execution = 0

    def __str__(self):
        return f"{self.cores} Cores, {self.threads} Threads"

    def populate_from_file(self, file_path: str) -> None:
        with open(file_path, "r") as result:
            energy_pkg = result.readline().rstrip()
            energy_cores = result.readline().rstrip()
            time = result.readline().rstrip()
        self.energy_pkg = float(energy_pkg.split(",")[0])
        self.energy_cores = float(energy_cores.split(",")[0])
        time_split = time.split(",")
        self.user = float(time_split[0])
        self.sys = float(time_split[1])
        self.execution = float(time_split[2])
        return


for file in os.scandir(result_dir):
    fname = os.path.splitext(file.name)[0]  # remove file extension
    key, constellation = fname.split(delimiter)
    cores, threads = constellation.split(",")
    bench = Bench(int(cores), int(threads))
    bench_dict.setdefault(key, []).append(bench)
    bench.populate_from_file(file.path)


for name, benchs in bench_dict.items():
    fig, ax = plt.subplots()
    x_axes, y_axes = (list() for i in range(2))
    for b in benchs:
        for time in [b.user, b.sys, b.execution]:
            x_axes.append(b.cores + "/" + b.threads)
            y_axes.append(time)

