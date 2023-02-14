import os, sys, glob
import matplotlib
import matplotlib.pyplot as plt
from statistics import fmean
import numpy as np
import argparse
from pathlib import Path
import shutil
from enum import Enum, auto
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style


# Setup
result_dir = "./results"
delimiter = "#"
# Don't add a trailing slash to yout paths
pictures = {
        'pics': './pics',
        'full_energy': './pics/energy',
        'full_time': './pics/exec_time',
        'half_energy': './pics/energy_half',
        'half_time': './pics/exec_time_half'

}
### Setup Done

# search for latest results
result_dir = max(glob.glob(os.path.join(result_dir, '*/')), key=os.path.getmtime)
### do not touch
bench_dict = dict()
half_bench_dict = dict()
thread_list = set()
core_list = set()
file_output = None

class Output(Enum):
    SVG = auto()
    PNG = auto()

class Bench:
    def __init__(self, cores: int, threads: int):
        self.threads = threads
        self.cores = cores
        self.energy_pkg = list()
        self.energy_cores = list()
        self.time = list()

    def __str__(self) -> str:
        return f"{self.cores} Cores, {self.threads} Threads"

    def populate_from_file(self, file_path: str) -> None:
        with open(file_path, "r") as result:
            line = result.readline().rstrip()
            while line.startswith('#'):
                line = result.readline().rstrip()
            while line:
                time = line
                energy_pkg = result.readline().rstrip()
                energy_cores = result.readline().rstrip()
                self.energy_pkg.append(float(energy_pkg.split(",")[0]))
                self.energy_cores.append(float(energy_cores.split(",")[0]))
                self.time.append(float("{:.1f}".format(float(time.split(",")[0]) * (10**-9))))
                # is there more? -> repetitions
                line = result.readline().rstrip()
        return


class HalfBench(Bench):
    def __init__(self, cores: int, threads: int, target_cores: int, target_threads: int):
        self.target_cores = target_cores
        self.target_threads = target_threads
        super().__init__(cores, threads)


### https://matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html
def heatmap(data, row_labels, col_labels, ax=None,
            cbar_kw=None, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (M, N).
    row_labels
        A list or array of length M with the labels for the rows.
    col_labels
        A list or array of length N with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if ax is None:
        ax = plt.gca()

    if cbar_kw is None:
        cbar_kw = {}

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # Show all ticks and label them with the respective list entries.
    ax.set_xticks(np.arange(data.shape[1]), labels=col_labels)
    ax.set_yticks(np.arange(data.shape[0]), labels=row_labels)

    # Let the horizontal axes labeling appear on top.
    #ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

    # Rotate the tick labels and set their alignment.
    #plt.setp(ax.get_xticklabels(), rotation=-30, ha="right", rotation_mode="anchor")

    # Turn spines off and create white grid.
    ax.spines[:].set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
                     textcolors=("black", "white"),
                     threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        `matplotlib.ticker.Formatter`.  Optional.
    textcolors
        A pair of colors.  The first is used for values below a threshold,
        the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to `text` used to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a `Text` for each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts
###

def generate_full(x_ax: list, y_ax: list, data_array: list, bench_name: str, folder: str, fname: str) -> None:
    plt.style.use('ggplot')
    fig, ax = plt.subplots()
    ax.set_ylabel("Threads")
    ax.set_xlabel("Cores")
    ax.grid(None)
    if "energy" in fname:
        ax.set_title("Package Energy {}".format(bench_name))
        im, cbar = heatmap(np.array(data_array), y_ax, x_ax, ax=ax,
                    cmap="YlGn", cbarlabel="Joules")
        texts = annotate_heatmap(im, valfmt="{x:.1f} J")
    elif "time" in fname:
        ax.set_title("Execution Time {}".format(bench_name))
        im, cbar = heatmap(np.array(data_array), y_ax, x_ax, ax=ax,
                cmap="YlGn", cbarlabel="seconds")
        texts = annotate_heatmap(im, valfmt="{x:.1f} s")
    else:
        sys.exit(f"{Fore.RED}fname must contain energy or time. Exiting now.\n{Style.RESET_ALL}")
    if file_output.name == 'PNG':
        plt.savefig("{}/{}_{}.png".format(folder, fname, bench_name), dpi=300)
    else:
        plt.savefig("{}/{}_{}.svg".format(folder, fname, bench_name))
    plt.close()
    return


def full_heat_map():
    y_ax = sorted(thread_list, reverse=True)
    x_ax = sorted(core_list)
    for name, benchs in bench_dict.items():
        benchs.sort(key=lambda b: (b.threads, -b.cores), reverse=True)
        print("Generating heat map for {}".format(name))

        energy = [benchs[i:i+len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        exec_time = [benchs[i:i+len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        for i in range(len(energy)):
            for j in range(len(energy[i])):
                energy[i][j] = fmean(energy[i][j].energy_pkg)
                exec_time[i][j] = fmean(exec_time[i][j].time)
        generate_full(x_ax, y_ax, energy, name, pictures.get("full_energy"), "energy")
        generate_full(x_ax, y_ax, exec_time, name, pictures.get("full_time"), "exec_time")


def half_heat_map():
    for name, benchs in half_bench_dict.items():
        print("Generating half heat map for {}".format(name))
        full_benchs = bench_dict.get(name)
        for half_bench in benchs:
            selection = list()
            for b in full_benchs:
                if (b.threads == half_bench.threads and (b.cores == half_bench.cores or b.cores == half_bench.threads)):
                    selection.append(b)
            selection.sort(key=lambda b: b.cores, reverse=True)
            selection.insert(1, half_bench)
            if len(selection) != 3:
                print(f"{Fore.RED}Something with the half benchs went wrong. Could not find matching full benchs.{Style.RESET_ALL}")
                return
            y_ax = [half_bench.threads]
            x_ax = [half_bench.threads, "half", half_bench.cores]
            energy = [[fmean(i.energy_pkg) for i in selection]]
            exec_time = [[fmean(i.time) for i in selection]]
            generate_full(x_ax, y_ax, energy, name, pictures.get("half_energy"), "energy")
            generate_full(x_ax, y_ax, exec_time, name, pictures.get("half_time"), "exec_time")


def main():
    colorama_init()
    # check Python version
    MIN_PYTHON = (3, 6) #enum auto
    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', required=True, choices=['png', 'svg'],  help='Do you want png or svg?')
    parser.add_argument('--clean', action='store_true', help='Set this flag if you want to clean up before running.')
    args = parser.parse_args()

    global file_output
    if args.output == 'png':
        file_output = Output.PNG
    else:
        file_output = Output.SVG

    if args.clean and os.path.exists(pictures.get('pics')):
        shutil.rmtree(pictures.get('pics'))

    for folder in pictures.values():
        Path(folder).mkdir(parents=True, exist_ok=True)

    full = half = 0

    for file in os.scandir(result_dir):
        if ".log" in file.name:
            continue
        fname = os.path.splitext(file.name)[0]  # remove file extension
        if "_half" in fname:
            key, constellation, target = fname.split(delimiter)
            key = key[:-5]
            cores, threads = constellation.split(",")
            target_c, target_t = target.split(",")
            bench = HalfBench(int(cores), int(threads), int(target_c), int(target_t))
            bench.populate_from_file(file.path)
            half_bench_dict.setdefault(key, []).append(bench)
            half += 1
        else:
            key, constellation = fname.split(delimiter)
            cores, threads = constellation.split(",")
            bench = Bench(int(cores), int(threads))
            bench.populate_from_file(file.path)
            bench_dict.setdefault(key, []).append(bench)
            thread_list.add(int(threads))
            core_list.add(int(cores))
            full += 1

    print(f"{Fore.YELLOW}Found {full+half} result files with {len(bench_dict.keys())} unique benchmarks.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}This includes {half} result files of half benchmarks.{Style.RESET_ALL}")
    print(f"\n{Fore.BLUE}Generating full heat maps.{Style.RESET_ALL}")
    full_heat_map()
    if half > 0:
        print(f"\n{Fore.BLUE}Generating half heat maps.{Style.RESET_ALL}")
        half_heat_map()
    return

if __name__ == "__main__":
   main()
