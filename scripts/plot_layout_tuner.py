"""
Plot Layout Tuner

Generates time history, PSD, spectrogram, and statistics plots from the
sample HDF5 data so layouts can be tuned locally. Edit the JSON config
output and re-run to iterate on formatting.

Usage:
    python scripts/plot_layout_tuner.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from types import SimpleNamespace

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spectral_edge.core.psd import calculate_psd_welch, calculate_psd_maximax
from spectral_edge.batch.spectrogram_generator import generate_spectrogram
from spectral_edge.batch.statistics import compute_statistics
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.utils.plot_theme import apply_light_matplotlib_theme, style_axes, style_colorbar


DEFAULT_PARAMS = {
    "time_window_seconds": 20.0,
    "max_time_points": 10000,
    "psd_method": "welch",
    "psd_df": 5.0,
    "psd_window": "hann",
    "psd_overlap_percent": 50.0,
    "psd_use_efficient_fft": True,
    "maximax_window": 1.0,
    "spectrogram_df": 5.0,
    "spectrogram_overlap_percent": 50.0,
    "spectrogram_snr_threshold": 20.0,
    "spectrogram_colormap": "viridis",
    "figure_sizes": {
        "time_history": [10, 3],
        "psd": [5.5, 5.5],
        "spectrogram": [6, 4],
        "pdf": [4, 4],
        "running_stat": [6, 1.3]
    },
    "font_size": 8.5,
    "dpi": 300
}


def ensure_sample_data(root: Path) -> Path:
    data_path = root / "data" / "sample_flight_data.hdf5"
    if data_path.exists():
        return data_path

    script_path = root / "scripts" / "generate_sample_hdf5.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Missing {script_path}")

    subprocess.run(["python", str(script_path)], check=True)
    if not data_path.exists():
        raise FileNotFoundError("Sample HDF5 was not generated as expected.")
    return data_path


def load_params(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    params_path = output_dir / "plot_template_params.json"
    if params_path.exists():
        return json.loads(params_path.read_text(encoding="utf-8"))

    params_path.write_text(json.dumps(DEFAULT_PARAMS, indent=2), encoding="utf-8")
    return DEFAULT_PARAMS


def decimate(time_array: np.ndarray, signal_array: np.ndarray, max_points: int):
    if len(time_array) <= max_points:
        return time_array, signal_array
    step = max(1, len(time_array) // max_points)
    return time_array[::step], signal_array[::step]


def save_plot(fig, output_path: Path, dpi: int):
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

def scaled_size(size, width_scale=1.0, height_scale=1.0):
    """Scale a [width, height] figure size tuple/list."""
    return (size[0] * width_scale, size[1] * height_scale)

def apply_axis_styling(ax, font_size: float):
    """Apply consistent axis styling for layout tuning outputs."""
    tick_font_size = max(6.5, font_size - 1.0)
    ax.tick_params(axis="both", which="both", direction="in", top=True, right=True, labelsize=tick_font_size)
    ax.xaxis.label.set_size(font_size)
    ax.yaxis.label.set_size(font_size)
    ax.title.set_size(font_size + 1)
    ax.minorticks_on()
    ax.grid(which="major", alpha=0.55, linewidth=0.7)
    ax.grid(which="minor", alpha=0.25, linewidth=0.5)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "plot_layout_output"
    params = load_params(output_dir)
    data_path = ensure_sample_data(repo_root)

    loader = HDF5FlightDataLoader(str(data_path))
    flight_key = loader.get_flight_keys()[0]
    channel = loader.get_channels(flight_key)[0]

    data = loader.load_channel_data(
        flight_key,
        channel.channel_key,
        start_time=0.0,
        end_time=params["time_window_seconds"],
        decimate_for_display=False
    )
    time_full = data["time_full"]
    signal_full = data["data_full"]
    sample_rate = float(data.get("sample_rate", 0.0))
    units = channel.units

    time_plot, signal_plot = decimate(time_full, signal_full, params["max_time_points"])

    apply_light_matplotlib_theme()
    base_font_size = float(params.get("font_size", 8.5))
    plt.rcParams.update({
        "font.size": base_font_size,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    })

    # Time history
    fig, ax = plt.subplots(figsize=params["figure_sizes"]["time_history"])
    ax.plot(time_plot, signal_plot, linewidth=1.3, color="#0039a6")
    ylabel = f"Amplitude ({units})" if units else "Amplitude"
    style_axes(ax, "Time History", "Time (s)", ylabel)
    apply_axis_styling(ax, base_font_size)
    fig.tight_layout()
    save_plot(fig, output_dir / "time_history.png", params["dpi"])

    # PSD
    if params["psd_method"] == "maximax":
        freqs, psd_vals = calculate_psd_maximax(
            signal_full,
            sample_rate,
            maximax_window=params["maximax_window"],
            overlap_percent=params["psd_overlap_percent"],
            window=params["psd_window"],
            df=params["psd_df"],
            use_efficient_fft=params["psd_use_efficient_fft"]
        )
    else:
        freqs, psd_vals = calculate_psd_welch(
            signal_full,
            sample_rate,
            window=params["psd_window"],
            df=params["psd_df"],
            use_efficient_fft=params["psd_use_efficient_fft"]
        )

    psd_font_size = float(params.get("psd_font_size", base_font_size))
    fig, ax = plt.subplots(figsize=scaled_size(params["figure_sizes"]["psd"], width_scale=1.2, height_scale=1.0))
    ax.loglog(freqs, psd_vals, linewidth=1.6, color="#0039a6")
    ylabel = f"PSD ({units}^2/Hz)" if units else "PSD"
    style_axes(ax, "PSD", "Frequency (Hz)", ylabel)
    apply_axis_styling(ax, psd_font_size)
    fig.tight_layout()
    save_plot(fig, output_dir / "psd.png", params["dpi"])

    # Spectrogram
    spec_freqs, spec_times, Sxx = generate_spectrogram(
        signal_full,
        sample_rate,
        desired_df=params["spectrogram_df"],
        overlap_percent=params["spectrogram_overlap_percent"],
        snr_threshold=params["spectrogram_snr_threshold"],
        use_efficient_fft=True
    )
    Sxx_db = 10 * np.log10(Sxx + 1e-12)
    fig, ax = plt.subplots(figsize=params["figure_sizes"]["spectrogram"])
    im = ax.pcolormesh(
        spec_times,
        spec_freqs,
        Sxx_db,
        shading="auto",
        cmap=params["spectrogram_colormap"]
    )
    style_axes(ax, "Spectrogram", "Time (s)", "Frequency (Hz)")
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("PSD (dB)")
    style_colorbar(cbar)
    apply_axis_styling(ax, base_font_size)
    ax.grid(False, which="major")
    ax.grid(False, which="minor")
    cbar.ax.tick_params(direction="in", labelsize=base_font_size)
    cbar.ax.yaxis.label.set_size(base_font_size)
    fig.tight_layout()
    save_plot(fig, output_dir / "spectrogram.png", params["dpi"])

    # Statistics
    stats_config = SimpleNamespace(
        pdf_bins=50,
        running_window_seconds=1.0,
        max_plot_points=5000,
        show_mean=True,
        show_std=True,
        show_skewness=True,
        show_kurtosis=True,
        show_normal=True,
        show_rayleigh=False,
        show_uniform=False
    )
    stats = compute_statistics(signal_full, sample_rate, stats_config)

    # PDF plot
    pdf_data = stats["pdf"]
    stats_font_size = float(params.get("stats_font_size", base_font_size))
    fig, ax = plt.subplots(figsize=scaled_size(params["figure_sizes"]["pdf"], width_scale=1.0, height_scale=1.0))
    ax.plot(pdf_data["bins"], pdf_data["counts"], linewidth=1.2, color="#0039a6")
    style_axes(ax, "Probability Density", "Value", "Density")
    apply_axis_styling(ax, stats_font_size)
    max_abs = max(abs(float(pdf_data["bins"].min())), abs(float(pdf_data["bins"].max())))
    if max_abs > 0:
        ax.set_xlim(-max_abs, max_abs)
    fig.tight_layout()
    save_plot(fig, output_dir / "stats_pdf.png", params["dpi"])

    # Running stats plots
    running = stats["running"]
    for key, title in [
        ("mean", "Running Mean"),
        ("std", "Running Std"),
        ("skewness", "Running Skewness"),
        ("kurtosis", "Running Kurtosis"),
    ]:
        fig, ax = plt.subplots(figsize=scaled_size(params["figure_sizes"]["running_stat"], width_scale=1.0, height_scale=2.0))
        time_key = "skewness_time" if key in {"skewness", "kurtosis"} else "time"
        time = running.get(time_key)
        values = running.get(key)
        if time is None or values is None or len(time) == 0:
            style_axes(ax, title, "Time (s)", key.title())
            ax.text(0.5, 0.5, "Not enough data for running stats",
                    ha="center", va="center", transform=ax.transAxes)
        else:
            ax.plot(time, values, linewidth=1.1, color="#0039a6")
            style_axes(ax, title, "Time (s)", key.title())
        apply_axis_styling(ax, stats_font_size)
        fig.tight_layout()
        save_plot(fig, output_dir / f"stats_{key}.png", params["dpi"])

    loader.close()
    print(f"Plots written to: {output_dir}")
    print(f"Edit params in: {output_dir / 'plot_template_params.json'}")


if __name__ == "__main__":
    main()
