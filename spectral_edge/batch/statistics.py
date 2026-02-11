"""
Batch statistics utilities for report generation.
"""

from typing import Dict, Tuple
import numpy as np
from scipy import stats
from scipy.ndimage import uniform_filter1d
import matplotlib

matplotlib.use("Agg")

from spectral_edge.utils.plot_theme import (
    apply_light_matplotlib_theme,
    style_axes,
    apply_axis_styling,
    BASE_FONT_SIZE,
    LINE_COLOR,
)
from spectral_edge.utils.statistics_overlays import (
    fit_rayleigh_from_signal,
    build_rayleigh_curve,
)


def compute_statistics(
    signal: np.ndarray,
    sample_rate: float,
    stats_config
) -> Dict[str, Dict]:
    """
    Compute PDF and running statistics for a signal.

    Returns
    -------
    dict with keys:
      pdf, running, overall
    """
    signal = np.asarray(signal)
    pdf_bins = int(getattr(stats_config, "pdf_bins", 50))
    window_seconds = float(getattr(stats_config, "running_window_seconds", 1.0))
    max_plot_points = int(getattr(stats_config, "max_plot_points", 5000))

    counts, bin_edges = np.histogram(signal, bins=pdf_bins, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    mean = float(np.mean(signal))
    std = float(np.std(signal))
    rms = float(np.sqrt(np.mean(signal ** 2)))
    crest_factor = float(np.max(np.abs(signal)) / rms) if rms > 1e-12 else 0.0

    # Running stats
    window_samples = max(10, int(window_seconds * sample_rate))
    running = {}
    if len(signal) >= window_samples:
        signal_float = signal.astype(np.float64)
        running_mean = uniform_filter1d(signal_float, size=window_samples, mode="nearest")
        running_sq = uniform_filter1d(signal_float ** 2, size=window_samples, mode="nearest")
        running_std = np.sqrt(np.maximum(running_sq - running_mean ** 2, 0))

        # Downsample for plotting
        if len(running_mean) > max_plot_points:
            step = max(1, len(running_mean) // max_plot_points)
            running_mean = running_mean[::step]
            running_std = running_std[::step]
            time = np.arange(len(running_mean)) * step / sample_rate
        else:
            time = np.arange(len(running_mean)) / sample_rate

        running["time"] = time
        running["mean"] = running_mean
        running["std"] = running_std

        # Skewness/kurtosis sampled
        n_samples = min(200, len(signal) // window_samples)
        if n_samples > 0:
            sample_step = len(signal) // n_samples
            running_skewness = np.zeros(n_samples)
            running_kurtosis = np.zeros(n_samples)
            skewness_time = np.zeros(n_samples)

            for j in range(n_samples):
                start_idx = j * sample_step
                end_idx = min(start_idx + window_samples, len(signal))
                window = signal[start_idx:end_idx]
                if len(window) > 10:
                    running_skewness[j] = stats.skew(window)
                    running_kurtosis[j] = stats.kurtosis(window)
                skewness_time[j] = start_idx / sample_rate

            running["skewness_time"] = skewness_time
            running["skewness"] = running_skewness
            running["kurtosis"] = running_kurtosis

    # Overall skew/kurtosis
    if len(signal) > 100000:
        sample_indices = np.random.choice(len(signal), 100000, replace=False)
        signal_sample = signal[sample_indices]
        skewness = float(stats.skew(signal_sample))
        kurtosis = float(stats.kurtosis(signal_sample))
    else:
        skewness = float(stats.skew(signal))
        kurtosis = float(stats.kurtosis(signal))

    rayleigh_scale, rayleigh_x_max = fit_rayleigh_from_signal(signal)

    return {
        "pdf": {
            "bins": bin_centers,
            "counts": counts,
            "mean": mean,
            "std": std,
            "rayleigh_scale": rayleigh_scale,
            "rayleigh_x_max": rayleigh_x_max,
        },
        "running": running,
        "overall": {
            "mean": mean,
            "std": std,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "min": float(np.min(signal)),
            "max": float(np.max(signal)),
            "rms": rms,
            "crest_factor": crest_factor
        }
    }


def plot_pdf(pdf_data: Dict, stats_config) -> Tuple["mpl.Figure", "mpl.Axes"]:
    """Create a PDF plot with optional overlays."""
    import matplotlib.pyplot as plt

    apply_light_matplotlib_theme()
    fig, ax = plt.subplots(figsize=(4, 4))
    bins = pdf_data["bins"]
    counts = pdf_data["counts"]
    mean = pdf_data["mean"]
    std = pdf_data["std"]

    ax.plot(bins, counts, linewidth=0.9, label="PDF", color=LINE_COLOR)

    x = np.linspace(bins.min(), bins.max(), 400)
    if getattr(stats_config, "show_normal", False) and np.isfinite(std) and std > 0:
        ax.plot(x, stats.norm.pdf(x, mean, std), linestyle="--", linewidth=0.8, color="#d62728", label="Normal")
    if getattr(stats_config, "show_rayleigh", False):
        rayleigh_x, rayleigh_y = build_rayleigh_curve(
            pdf_data.get("rayleigh_scale", None),
            pdf_data.get("rayleigh_x_max", None),
        )
        if rayleigh_x is not None and rayleigh_y is not None:
            ax.plot(rayleigh_x, rayleigh_y, linestyle="--", linewidth=0.8, label="Rayleigh")
    if getattr(stats_config, "show_uniform", False):
        ax.plot(
            x,
            stats.uniform.pdf(x, loc=bins.min(), scale=bins.max() - bins.min()),
            linestyle="--",
            linewidth=0.8,
            label="Uniform",
        )

    style_axes(ax, "Probability Density", "Value", "Density")
    apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
    max_abs = max(abs(float(bins.min())), abs(float(bins.max())))
    if max_abs > 0:
        ax.set_xlim(-max_abs, max_abs)
    ax.legend(fontsize=max(6.5, BASE_FONT_SIZE - 1.0), loc="best")
    fig.tight_layout()
    return fig, ax


def plot_running_stat(running_data: Dict, stat_key: str, title: str, y_label: str) -> Tuple["mpl.Figure", "mpl.Axes"]:
    """Create a single running statistic plot."""
    import matplotlib.pyplot as plt

    apply_light_matplotlib_theme()
    fig, ax = plt.subplots(figsize=(8.35, 1.55))
    if not running_data:
        style_axes(ax, title, "Time (s)", y_label)
        apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
        ax.text(0.5, 0.5, "Not enough data for running stats",
                ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        return fig, ax

    time = running_data["skewness_time"] if stat_key in {"skewness", "kurtosis"} else running_data.get("time")
    values = running_data.get(stat_key)
    if time is None or values is None or len(time) == 0:
        style_axes(ax, title, "Time (s)", y_label)
        apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
        ax.text(0.5, 0.5, "Not enough data for running stats",
                ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        return fig, ax

    ax.plot(time, values, linewidth=0.8, color=LINE_COLOR)
    style_axes(ax, title, "Time (s)", y_label)
    apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
    fig.tight_layout()
    return fig, ax


def plot_running_stats(running_data: Dict, stats_config) -> Tuple["mpl.Figure", "mpl.Axes"]:
    """Create running statistics plot (combined view)."""
    import matplotlib.pyplot as plt

    apply_light_matplotlib_theme()
    fig, ax = plt.subplots(figsize=(6, 4))
    if not running_data:
        style_axes(ax, "Running Statistics", "Time (s)", "Value")
        apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
        ax.text(0.5, 0.5, "Not enough data for running stats",
                ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        return fig, ax

    time = running_data.get("time")
    if getattr(stats_config, "show_mean", True) and "mean" in running_data and time is not None:
        ax.plot(time, running_data["mean"], label="Mean", color=LINE_COLOR, linewidth=1.1)
    if getattr(stats_config, "show_std", True) and "std" in running_data and time is not None:
        ax.plot(time, running_data["std"], label="Std", linewidth=1.1)
    if getattr(stats_config, "show_skewness", False) and "skewness" in running_data:
        ax.plot(running_data["skewness_time"], running_data["skewness"], label="Skewness", linewidth=1.1)
    if getattr(stats_config, "show_kurtosis", False) and "kurtosis" in running_data:
        ax.plot(running_data["skewness_time"], running_data["kurtosis"], label="Kurtosis", linewidth=1.1)

    style_axes(ax, "Running Statistics", "Time (s)", "Value")
    apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
    ax.legend(fontsize=max(6.5, BASE_FONT_SIZE - 1.0), loc="best")
    fig.tight_layout()
    return fig, ax
