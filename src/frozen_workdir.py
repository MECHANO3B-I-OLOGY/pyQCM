"""
Working directory setup for the standalone (PyInstaller) Windows/macOS builds.

The software reads and writes its data folders (plot_opts, offset_data, raw_data,
selected_ranges, qcmd-plots, ...) relative to the current working directory.
Running from source, that is the repository root. A standalone app can be launched
from anywhere though (macOS starts .app bundles in '/', Windows shortcuts can set any
'Start in' folder), so pick a writable data folder, fill in any missing default files
that are bundled inside the executable, and change into it before the UI starts.
"""

import os
import shutil
import sys
from pathlib import Path

# folders bundled into the executable as 'datas' in windowsExec.spec / macExec.spec
BUNDLED_DIRS = ['plot_opts', 'offset_data', 'sample_generations', 'res']

# folders the software writes its outputs into
OUTPUT_DIRS = ['raw_data', 'selected_ranges', 'qcmd-plots/modeling']

# interactive plot/modeling stats files, seeded with only their headers so a fresh install has no stale ranges
STATS_FILE_HEADERS = {
    'clean_all_stats_rf.csv': "overtone,Dfreq_average,Dfreq_std_dev,Dfreq_median,range_name,x_lower,x_upper,data_source",
    'clean_all_stats_dis.csv': "overtone,Ddis_average,Ddis_std_dev,Ddis_median,range_name,x_lower,x_upper,data_source",
    'raw_all_stats_rf.csv': "overtone,Dfreq_average,Dfreq_std_dev,Dfreq_median,range_name,x_lower,x_upper,data_source",
    'raw_all_stats_dis.csv': "overtone,Ddis_average,Ddis_std_dev,Ddis_median,range_name,x_lower,x_upper,data_source",
    'Sauerbrey_stats.csv': "overtone,avg_Df,std_dev_Df,avg_Dm,std_dev_Dm,C,range_name,data_source",
    'Sauerbrey_ranges.csv': "range_name,lower_bound,upper_bound,data_source",
    'sauerbrey_output.csv': "avg_Df,avg_Dm,range_name,data_source",
    'thin_film_liquid_output.csv': "n*Df,bandwidth_shift,bandwidth_shift_FIT,range_name,data_source",
    'thin_film_air_output.csv': "sq_overtones,delta_gamma_norm,delta_gamma_norm_fit,delta_freqs_norm,delta_freq_norm_fit,range_name,data_source",
    'crystal_thickness_output.csv': "overtone,offset_vals,offset_vals_FIT",
}


def is_frozen():
    return getattr(sys, 'frozen', False)


def candidate_workdirs():
    """data folder locations in order of preference"""
    documents = Path.home() / 'Documents' / 'pyQCM'
    home = Path.home() / 'pyQCM'
    if sys.platform == 'darwin':
        # the executable lives inside pyQCM.app/Contents/MacOS, which may be read-only (/Applications, translocated downloads)
        return [documents, home]

    # Windows/Linux: keep data next to the executable, as laid out in the release archive
    exe_dir = Path(sys.executable).resolve().parent
    return [exe_dir, documents, home]


def is_writable(folder):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / '.pyqcm_write_test'
        probe.write_text('')
        probe.unlink()
        return True
    except OSError:
        return False


def copy_missing_files(src, dst):
    """copy src folder into dst without overwriting files the user already has (e.g. saved plot customizations)"""
    for root, _, files in os.walk(src):
        target_dir = dst / Path(root).relative_to(src)
        target_dir.mkdir(parents=True, exist_ok=True)
        for fn in files:
            target = target_dir / fn
            if not target.exists():
                shutil.copy2(os.path.join(root, fn), target)


def setup_frozen_workdir():
    """when running as a standalone app, change into a writable data folder populated with the default files

    Returns:
        Path: the working directory the software will read from and write to
    """
    if not is_frozen():
        return Path.cwd()

    workdir = next((folder for folder in candidate_workdirs() if is_writable(folder)), None)
    if workdir is None:
        raise RuntimeError("pyQCM could not find a writable folder to store its data in. Tried: " +
                           ", ".join(str(folder) for folder in candidate_workdirs()))

    # PyInstaller extracts/places bundled datas in sys._MEIPASS
    bundle_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
    for name in BUNDLED_DIRS:
        if (bundle_dir / name).is_dir():
            copy_missing_files(bundle_dir / name, workdir / name)

    for name in OUTPUT_DIRS:
        (workdir / name).mkdir(parents=True, exist_ok=True)

    for fn, header in STATS_FILE_HEADERS.items():
        stats_fp = workdir / 'selected_ranges' / fn
        if not stats_fp.exists():
            stats_fp.write_text(header + '\n')

    os.chdir(workdir)
    print(f"pyQCM data folder: {workdir}")
    return workdir
