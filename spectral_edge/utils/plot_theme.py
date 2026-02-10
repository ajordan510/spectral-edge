"""
Light theme utilities for Matplotlib output plots.

Centralizes styling so report visuals stay consistent.
"""

from typing import Optional
import os

import matplotlib as mpl
from cycler import cycler

BASE_FONT_SIZE = 8.5
LINE_COLOR = "#0039a6"
GRID_COLOR = "#c0c0c0"


def apply_light_matplotlib_theme() -> None:
    """Apply a consistent light theme for Matplotlib plots."""
    mpl.rcParams.update({
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#1f2937",
        "axes.labelcolor": "#111827",
        "axes.titlesize": BASE_FONT_SIZE + 1.0,
        "axes.titleweight": "bold",
        "xtick.color": "#111827",
        "ytick.color": "#111827",
        "grid.color": GRID_COLOR,
        "grid.alpha": 0.7,
        "grid.linestyle": "--",
        "text.color": "#111827",
        "legend.frameon": True,
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#d1d5db",
        "font.size": BASE_FONT_SIZE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "axes.prop_cycle": cycler(
            color=[LINE_COLOR, "#16a34a", "#f59e0b", "#dc2626", "#9333ea", "#0ea5e9"]
        ),
    })


def style_axes(ax, title: Optional[str], xlabel: str, ylabel: str) -> None:
    """Apply consistent axes styling."""
    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", axis="both")
    for spine in ax.spines.values():
        spine.set_color("#1f2937")


def apply_axis_styling(ax, font_size: float = BASE_FONT_SIZE, include_grid: bool = True) -> None:
    """Apply axis tick/font/grid styling to match report tuning outputs."""
    tick_font_size = max(6.5, font_size - 1.0)
    ax.tick_params(axis="both", which="both", direction="in", top=True, right=True, labelsize=tick_font_size)
    ax.xaxis.label.set_size(font_size)
    ax.yaxis.label.set_size(font_size)
    ax.title.set_size(font_size + 1.0)
    ax.minorticks_on()
    if include_grid:
        ax.grid(True, which="major", axis="both", alpha=0.7, linewidth=0.6, linestyle="--")
        ax.grid(True, which="minor", axis="both", alpha=0.35, linewidth=0.5, linestyle="--")
    else:
        ax.grid(False, which="major")
        ax.grid(False, which="minor")


def style_colorbar(cbar, font_size: float = BASE_FONT_SIZE) -> None:
    """Apply consistent colorbar styling."""
    cbar.ax.yaxis.label.set_color("#111827")
    cbar.ax.tick_params(colors="#111827", direction="in", labelsize=max(6.5, font_size - 1.0))
    cbar.ax.yaxis.label.set_size(font_size)


def get_watermark_text() -> str:
    """Return watermark text for plots."""
    return os.getenv("PYMARVIN_WATERMARK", "pyMARVIN v0.1.0 (Epic 1)")


def add_watermark(ax, text: Optional[str] = None, font_size: float = BASE_FONT_SIZE) -> None:
    """Add a light watermark to the top-right of a plot."""
    label = text or get_watermark_text()
    ax.text(
        0.99,
        1.02,
        label,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        color="#9ca3af",
        fontsize=max(6.0, font_size - 2.0),
    )
