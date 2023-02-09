import os, sys
import glob
import matplotlib
import matplotlib.pyplot as plt
from statistics import fmean
import numpy as np
import argparse
from pathlib import Path
import shutil


# Setup
result_dir = "./results"
delimiter = "#"
# search for latest results
result_dir = max(glob.glob(os.path.join(result_dir, '*/')), key=os.path.getmtime)
### do not touch
bench_dict = dict()
thread_list = set()
core_list = set()

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


def heat_map():
    y_ax = sorted(thread_list, reverse=True)
    x_ax = sorted(core_list)
    for name, benchs in bench_dict.items():
        benchs.sort(key=lambda b: (b.threads, -b.cores), reverse=True)
        print("Generating heat map for {}".format(name))

        energy = [benchs[i:i+len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        exec_time = [benchs[i:i+len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        lol = [benchs[i:i+len(x_ax)] for i in range(0, len(benchs), len(x_ax))]
        for i in range(len(energy)):
            for j in range(len(energy[i])):
                energy[i][j] = fmean(energy[i][j].energy_pkg)
                exec_time[i][j] = fmean(exec_time[i][j].execution)
                lol[i][j] = "C"+str(lol[i][j].cores) + " " + "T"+str(lol[i][j].threads)

        print(lol)

        plt.style.use('ggplot')
        fig, ax = plt.subplots()
        ax.set_ylabel("threads")
        ax.set_xlabel("cores")
        ax.set_title("Package Energy")
        ax.grid(None)

        im, cbar = heatmap(np.array(energy), y_ax, x_ax, ax=ax,
                cmap="YlGn", cbarlabel="{}".format(name))
        texts = annotate_heatmap(im, valfmt="{x:.1f} J")

        plt.savefig("pics/energy_{}.png".format(name), dpi=300)
        plt.close()

        plt.style.use('ggplot')
        fig, ax = plt.subplots()
        ax.set_ylabel("threads")
        ax.set_xlabel("cores")
        ax.set_title("Execution Time")
        ax.grid(None)

        im, cbar = heatmap(np.array(exec_time), y_ax, x_ax, ax=ax,
                cmap="YlGn", cbarlabel="{}".format(name))
        texts = annotate_heatmap(im, valfmt="{x:.1f} s")

        plt.savefig("pics/exectime_{}.png".format(name), dpi=300)
        plt.close()

def line_plots(output: str):
    for name, benchs in bench_dict.items():
        benchs.sort(key=lambda b: (b.cores+b.threads, b.cores, -b.threads), reverse=True)
        print("Generating plot for {}".format(name))
        x_axes, y_user, y_sys, y_exe, y_e_pkg, y_e_core = (list() for i in range(6))
        for b in benchs:
            x_axes.append(str(b.cores) + "/" + str(b.threads))
            y_user.append(fmean(b.user))
            y_sys.append(fmean(b.sys))
            y_exe.append(fmean(b.execution))
            y_e_pkg.append(fmean(b.energy_pkg))
            y_e_core.append(fmean(b.energy_cores))

        plt.style.use('ggplot')
        fig, ax = plt.subplots()

        ax.set_ylabel("time in seconds")
        ax.set_xlabel("cores/threads")
        l1, = ax.plot(x_axes, y_user, 'o-', label="user time")
        l2, = ax.plot(x_axes, y_sys, 'o-', label="sys time")
        l3, = ax.plot(x_axes, y_exe, 'o-', label="exe time")

        twin = ax.twinx()
        twin.grid(None)
        twin.set_ylabel("energy in joules")
        # C3 = 3rd color in current palette
        l4, = twin.plot(x_axes, y_e_core, 'D-', label="energy cores", color="C3")
        l5, = twin.plot(x_axes, y_e_pkg, 'D-', label="energy package", color="C4")

        plt.legend(loc='best', facecolor='white', fancybox=True, framealpha=0.7, handles=[l1,l2,l3,l4,l5])

        if output == 'png':
            plt.savefig("pics/{}.png".format(name), dpi=300)
        else:
            fig.savefig("pics/{}.svg".format(name))
        plt.close()


def main():
    # check Python version
    MIN_PYTHON = (3, 5)
    if sys.version_info < MIN_PYTHON:
        sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', required=True, choices=['png', 'svg'],  help='Do you want png or svg?')
    parser.add_argument('--clean', action='store_true', help='Set this flag if you want to clean up before running.')
    args = parser.parse_args()

    if args.clean:
        shutil.rmtree('pics')

    Path('pics').mkdir(parents=True, exist_ok=True)
    cnt = 0

    for file in os.scandir(result_dir):
        if ".log" in file.name:
            continue
        fname = os.path.splitext(file.name)[0]  # remove file extension
        key, constellation = fname.split(delimiter)
        cores, threads = constellation.split(",")
        bench = Bench(int(cores), int(threads))
        bench_dict.setdefault(key, []).append(bench)
        bench.populate_from_file(file.path)
        thread_list.add(int(threads))
        core_list.add(int(cores))
        cnt += 1

    print("Found {} result files with {} unique benchmarks.".format(cnt, len(bench_dict.items())))
    line_plots(args.output)
    heat_map()
    return

if __name__ == "__main__":
   main()
