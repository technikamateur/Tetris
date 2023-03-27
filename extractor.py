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
pictures = {'pics': './pics', 'full_energy': './pics/energy', 'full_time': './pics/exec_time', 'half_energy': './pics/energy_half', 'half_time': './pics/exec_time_half'}
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
            while line:
                if line.startswith('#'):
                    line = result.readline().rstrip()
                    continue
                if 'duration_time' in line:
                    self.time.append(float("{:.1f}".format(float(line.split(",")[0]) * (10**-9))))
                elif 'energy-pkg' in line:
                    self.energy_pkg.append(float(line.split(",")[0]))  # cuts of everything behind ,
                elif 'energy-cores' in line:
                    self.energy_cores.append(float(line.split(",")[0]))
                else:
                    print(f"{Fore.YELLOW}Found unknown line: {line}.{Style.RESET_ALL}")
                # is there more? -> repetitions
                line = result.readline().rstrip()
        return



class HalfBench(Bench):

    def __init__(self, cores: int, threads: int, target_cores: int, target_threads: int):
        self.target_cores = target_cores
        self.target_threads = target_threads
        super().__init__(cores, threads)


### https://matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html
def heatmap(data, row_labels, col_labels, ax=None, cbar_kw=None, cbarlabel="", **kwargs):
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

    ax.set_xticks(np.arange(data.shape[1] + 1) - .5, minor=True)
    ax.set_yticks(np.arange(data.shape[0] + 1) - .5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def annotate_heatmap(im, data=None, valfmt="{x:.2f}", textcolors=("black", "white"), threshold=None, **textkw):
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
        threshold = im.norm(data.max()) / 2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center", verticalalignment="center")
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


def generate_heatmap(x_ax: list, y_ax: list, data_array: list, title: str, file_out: str) -> None:
    plt.style.use('ggplot')
    fig, ax = plt.subplots()
    ax.set_ylabel("Threads")
    ax.set_xlabel("Cores")
    ax.grid(None)
    ax.set_title(f"{title}")
    if "energy" in title.casefold():
        im, cbar = heatmap(np.array(data_array), y_ax, x_ax, ax=ax, cmap="YlGn", cbarlabel="Joules")
        texts = annotate_heatmap(im, valfmt="{x:.1f} J")
    elif "time" in title.casefold():
        im, cbar = heatmap(np.array(data_array), y_ax, x_ax, ax=ax, cmap="YlGn", cbarlabel="seconds")
        texts = annotate_heatmap(im, valfmt="{x:.1f} s")
    else:
        sys.exit(f"{Fore.RED}title must contain energy or time. Exiting now.\n{Style.RESET_ALL}")
    fig.tight_layout()
    if file_output.name == 'PNG':
        plt.savefig(f"{file_out}.png", dpi=300)
    else:
        plt.savefig(f"{file_out}.svg")
    plt.close()
    return


def generate_bars(x_ax: list, y_ax: str, vals: dict, title: str, file_out: str) -> None:
    plt.style.use('ggplot')
    max_ylim = [max(elem) for elem in vals.values()]  # max from each sublist
    max_ylim = round(1.2 * max(max_ylim))  # global max

    if len(vals.keys()) != 3:
        sys.exit(f"{Fore.RED}You are trying to plot something diffrent than 3 bars. This will not work.{Style.RESET_ALL}")

    x = np.arange(len(x_ax))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 0

    fig, ax = plt.subplots(constrained_layout=True)

    for attribute, measurement in vals.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        ax.bar_label(rects, padding=3)
        multiplier += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel(y_ax)
    ax.set_title(title)
    ax.set_xticks(x + width, x_ax)
    ax.legend(loc='upper left', ncols=3)
    ax.set_ylim(0, max_ylim)
    if file_output.name == 'PNG':
        plt.savefig(f"{file_out}.png", dpi=300)
    else:
        plt.savefig(f"{file_out}.svg")
    plt.close()
    return


def full_heat_map():
    y_ax = sorted(thread_list, reverse=True)
    x_ax = sorted(core_list)
    for name, benchs in bench_dict.items():
        benchs.sort(key=lambda b: (b.threads, -b.cores), reverse=True)
        print("Generating heat map for {}".format(name))

        energy = [benchs[i:i + len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        exec_time = [benchs[i:i + len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        for i in range(len(energy)):
            for j in range(len(energy[i])):
                energy[i][j] = fmean(energy[i][j].energy_pkg)
                exec_time[i][j] = fmean(exec_time[i][j].time)
        generate_heatmap(x_ax, y_ax, energy, f"Package Energy {name}", f"{pictures.get('full_energy')}/{name}")
        generate_heatmap(x_ax, y_ax, exec_time, f"Exe Time {name}", f"{pictures.get('full_time')}/{name}")


def half_heat_map():
    sources = set()
    for benchs in half_bench_dict.values():
        for hb in benchs:  # hb = half_bench
            sources.add((hb.cores, hb.threads))
    print(f"Found sources: {sources}")
    for name, hbenchs in half_bench_dict.items():
        print("Generating half heat map for {}".format(name))
        fbenchs = bench_dict.get(name)
        for source in sources:  # one diagram for every source (and bench of course)
            title = f"from {source[0]}C / {source[1]}T to"
            vals_energy = {'Full Source': list(), 'Half': list(), 'Full Target': list()}
            vals_time = {'Full Source': list(), 'Half': list(), 'Full Target': list()}
            x_ax = list()
            presearched_full = [fb for fb in fbenchs if fb.cores == source[0] and fb.threads == source[1]][0]
            search_array = [e for e in hbenchs if e.cores == source[0] and e.threads == source[1]]
            search_array.sort(key=lambda b: (b.target_cores, b.target_threads), reverse=True)
            for hb in search_array:
                for fb in fbenchs:
                    if (fb.threads == hb.target_threads and fb.cores == hb.target_cores):
                        vals_energy['Full Target'].append(fmean(fb.energy_pkg))
                        vals_time['Full Target'].append(fmean(fb.time))
                vals_energy['Full Source'].append(fmean(presearched_full.energy_pkg))
                vals_time['Full Source'].append(fmean(presearched_full.time))
                vals_energy['Half'].append(fmean(hb.energy_pkg))
                vals_time['Half'].append(fmean(hb.time))
                x_ax.append(f"{hb.target_cores}C / {hb.target_threads}T")
            # internal Check
            if ((len(vals_energy.get('Full Source')) != len(vals_energy.get('Half'))) or (len(vals_energy.get('Full Target')) != len(vals_energy.get('Half')))):
                print(f"{Fore.RED}Something with the half benchs went wrong. The length of the vals does not match. Therefore I cant create your plots.{Style.RESET_ALL}")
                return
            generate_bars(x_ax, "Energy [Joules]", vals_energy, f"Package Energy {name} {title}", f"{pictures.get('half_energy')}/{name}_{source[0]}C{source[1]}T")
            generate_bars(x_ax, "Time [s]", vals_time, f"Exe Time {name} {title}", f"{pictures.get('half_time')}/{name}_{source[0]}C{source[1]}T")

    return


''' OLD SHIT
            selection = list()
            for b in full_benchs:
                if ((b.threads == half_bench.threads and b.cores == half_bench.cores) or (b.threads == half_bench.target_threads and b.cores == half_bench.target_cores)):
                    selection.append(b)
            selection.sort(key=lambda b: b.cores, reverse=True)
            selection.insert(1, half_bench)
            if len(selection) != 3:
                print(f"{Fore.RED}Something with the half benchs went wrong. Exspected 3 benchs, but found {len(selection)} in list.{Style.RESET_ALL}")
                return
            y_ax = [f"From T{half_bench.threads} C{half_bench.cores} to T{half_bench.target_threads} C{half_bench.target_cores}"]
            x_ax = [half_bench.threads, "half", half_bench.cores]
            energy = [[fmean(i.energy_pkg) for i in selection]]
            exec_time = [[fmean(i.time) for i in selection]]
            generate_full(x_ax, y_ax, energy, name, pictures.get("half_energy"), "energy")
            generate_full(x_ax, y_ax, exec_time, name, pictures.get("half_time"), "exec_time")
'''


def main():
    colorama_init()
    # check Python version
    MIN_PYTHON = (3, 6)  #enum auto
    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', required=True, choices=['png', 'svg'], help='Select output format.')
    parser.add_argument('-g', '--generate', required=True, choices=['half', 'full', 'all'], help='Select what you would like to generate.')
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
    if args.generate != 'half':
        print(f"\n{Fore.BLUE}Generating full heat maps.{Style.RESET_ALL}")
        full_heat_map()
    else:
        print(f"\n{Fore.BLUE}Skipping full heat maps because of your choice.{Style.RESET_ALL}")
    if half > 0 and args.generate != 'full':
        print(f"\n{Fore.BLUE}Generating half heat maps.{Style.RESET_ALL}")
        half_heat_map()
    else:
        print(f"\n{Fore.BLUE}Skipping half heat maps because of your choice or there was no half bench.{Style.RESET_ALL}")
    return


if __name__ == "__main__":
    main()
