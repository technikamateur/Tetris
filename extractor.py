import os, glob

### Setup
result_dir = "./results"
delimiter = "#"
###

result_dir = max(glob.glob(os.path.join(result_dir, '*/')), key=os.path.getmtime)
bench_dict = dict()

class Bench:
    def __init__(self, cores: int, threads: int):
        self.threads = threads
        self.cores = cores
        self.energy_pkg = 0
        self.energy_cores = 0
        self.user = 0
        self.sys = 0
        self.execution = 0

    def populate_from_file(self, file_path: str) -> None:
        return

for file in os.scandir(result_dir):
    fname = os.path.splitext(file.name)[0]  # remove file extension
    key, constellation = fname.split(delimiter)
    cores, threads = constellation.split(",")
    bench = Bench(int(cores), int(threads))
    bench_dict.setdefault(key, []).append(bench)
    bench.populate_from_file(file.path)

print(bench_dict)
