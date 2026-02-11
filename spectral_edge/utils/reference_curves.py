"""Shared helpers for built-in and imported PSD reference curves."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import csv

import numpy as np


REFERENCE_CURVE_COLOR_PALETTE = [
    "#ff6b6b",
    "#ffd93d",
    "#6bcb77",
    "#4d96ff",
    "#ff6f91",
    "#845ec2",
]

BUILTIN_REFERENCE_CURVES: Dict[str, Dict[str, Any]] = {
    "minimum_screening": {
        "id": "minimum_screening",
        "name": "Minimum Screening",
        "frequencies": [20.0, 80.0, 800.0, 2000.0],
        "psd": [0.01, 0.04, 0.04, 0.01],
    },
    "minimum_screening_plus_3db": {
        "id": "minimum_screening_plus_3db",
        "name": "Minimum Screening + 3 dB",
        "frequencies": [20.0, 80.0, 800.0, 2000.0],
        "psd": [0.02, 0.08, 0.08, 0.02],
    },
}


def get_builtin_reference_curve_ids() -> List[str]:
    """Return built-in curve IDs in display order."""
    return list(BUILTIN_REFERENCE_CURVES.keys())


def build_builtin_reference_curve(
    builtin_id: str,
    *,
    enabled: bool = True,
    color: Optional[str] = None,
    line_style: str = "dashed",
) -> Dict[str, Any]:
    """Build a normalized built-in reference curve entry."""
    if builtin_id not in BUILTIN_REFERENCE_CURVES:
        raise ValueError(f"Unknown built-in reference curve: {builtin_id}")
    definition = BUILTIN_REFERENCE_CURVES[builtin_id]
    return sanitize_reference_curve(
        name=definition["name"],
        frequencies=definition["frequencies"],
        psd=definition["psd"],
        enabled=enabled,
        source="builtin",
        builtin_id=definition["id"],
        file_path=None,
        color=color,
        line_style=line_style,
    )


def load_reference_curve_csv(file_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Load a reference curve CSV with two numeric columns (frequency, PSD).

    Header rows are automatically ignored.
    """
    frequencies: List[float] = []
    psd_values: List[float] = []
    with Path(file_path).open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                frequency = float(str(row[0]).strip())
                psd = float(str(row[1]).strip())
            except ValueError:
                continue
            frequencies.append(frequency)
            psd_values.append(psd)

    if len(frequencies) < 2:
        raise ValueError("Reference curve CSV must contain at least two numeric data rows.")

    return np.asarray(frequencies, dtype=np.float64), np.asarray(psd_values, dtype=np.float64)


def sanitize_reference_curve(
    *,
    name: str,
    frequencies: Iterable[float],
    psd: Iterable[float],
    enabled: bool = True,
    source: str = "imported",
    builtin_id: Optional[str] = None,
    file_path: Optional[str] = None,
    color: Optional[str] = None,
    line_style: str = "dashed",
) -> Dict[str, Any]:
    """Validate and normalize reference curve data into canonical dict form."""
    curve_name = str(name).strip()
    if not curve_name:
        raise ValueError("Reference curve name cannot be empty.")

    frequencies_arr = np.asarray(list(frequencies), dtype=np.float64)
    psd_arr = np.asarray(list(psd), dtype=np.float64)

    if frequencies_arr.size < 2:
        raise ValueError("Reference curve must contain at least two frequency points.")
    if frequencies_arr.size != psd_arr.size:
        raise ValueError("Reference curve frequency and PSD arrays must have matching lengths.")
    if not np.all(np.isfinite(frequencies_arr)):
        raise ValueError("Reference curve frequencies must be finite numeric values.")
    if not np.all(np.isfinite(psd_arr)):
        raise ValueError("Reference curve PSD values must be finite numeric values.")
    if np.any(frequencies_arr <= 0):
        raise ValueError("Reference curve frequencies must be > 0 for log-scale plotting.")
    if np.any(psd_arr < 0):
        raise ValueError("Reference curve PSD values must be >= 0.")

    sort_idx = np.argsort(frequencies_arr)
    frequencies_arr = frequencies_arr[sort_idx]
    psd_arr = psd_arr[sort_idx]

    unique_freqs, unique_indices = np.unique(frequencies_arr, return_index=True)
    frequencies_arr = unique_freqs
    psd_arr = psd_arr[unique_indices]
    if frequencies_arr.size < 2:
        raise ValueError("Reference curve must contain at least two unique frequency points.")

    normalized_source = str(source).strip().lower()
    if normalized_source not in {"builtin", "imported"}:
        normalized_source = "imported"

    normalized_style = normalize_line_style(line_style)

    return {
        "name": curve_name,
        "frequencies": frequencies_arr.tolist(),
        "psd": psd_arr.tolist(),
        "enabled": bool(enabled),
        "source": normalized_source,
        "builtin_id": builtin_id if normalized_source == "builtin" else None,
        "file_path": file_path,
        "color": color,
        "line_style": normalized_style,
    }


def normalize_reference_curve_entry(curve: Any) -> Dict[str, Any]:
    """Normalize one curve entry from dict/dataclass/object into canonical dict form."""
    if curve is None:
        raise ValueError("Reference curve entry is empty.")
    if is_dataclass(curve):
        payload = asdict(curve)
    elif isinstance(curve, dict):
        payload = dict(curve)
    else:
        payload = {
            "name": getattr(curve, "name", ""),
            "frequencies": getattr(curve, "frequencies", []),
            "psd": getattr(curve, "psd", []),
            "enabled": getattr(curve, "enabled", True),
            "source": getattr(curve, "source", "imported"),
            "builtin_id": getattr(curve, "builtin_id", None),
            "file_path": getattr(curve, "file_path", None),
            "color": getattr(curve, "color", None),
            "line_style": getattr(curve, "line_style", "dashed"),
        }

    return sanitize_reference_curve(
        name=payload.get("name", ""),
        frequencies=payload.get("frequencies", []),
        psd=payload.get("psd", []),
        enabled=payload.get("enabled", True),
        source=payload.get("source", "imported"),
        builtin_id=payload.get("builtin_id"),
        file_path=payload.get("file_path"),
        color=payload.get("color"),
        line_style=payload.get("line_style", "dashed"),
    )


def dedupe_reference_curves(curves: Iterable[Any]) -> List[Dict[str, Any]]:
    """Deduplicate reference curves while preserving order (strictly for built-ins)."""
    deduped: List[Dict[str, Any]] = []
    seen_builtin_ids = set()
    for curve in curves:
        normalized = normalize_reference_curve_entry(curve)
        if normalized["source"] == "builtin":
            builtin_id = normalized.get("builtin_id")
            if builtin_id in seen_builtin_ids:
                continue
            seen_builtin_ids.add(builtin_id)
        deduped.append(normalized)
    return deduped


def prepare_reference_curves_for_plot(
    curves: Iterable[Any],
    *,
    freq_min: float,
    freq_max: float,
    clip_to_range: bool = True,
    logger=None,
) -> List[Dict[str, Any]]:
    """Prepare enabled reference curves for plotting with optional frequency clipping."""
    prepared: List[Dict[str, Any]] = []
    if freq_min <= 0 or freq_max <= 0 or freq_min >= freq_max:
        return prepared

    for idx, curve in enumerate(curves):
        try:
            normalized = normalize_reference_curve_entry(curve)
        except Exception as exc:
            if logger is not None:
                logger.warning(f"Skipping invalid reference curve at index {idx}: {exc}")
            continue

        if not normalized.get("enabled", True):
            continue

        freqs = np.asarray(normalized["frequencies"], dtype=np.float64)
        psd = np.asarray(normalized["psd"], dtype=np.float64)
        if clip_to_range:
            mask = (freqs >= freq_min) & (freqs <= freq_max)
            if not np.any(mask):
                continue
            plot_freq = freqs[mask]
            plot_psd = psd[mask]
            if plot_freq.size < 2:
                continue
        else:
            plot_freq = freqs
            plot_psd = psd

        prepared.append(
            {
                "name": normalized["name"],
                "frequencies": plot_freq,
                "psd": plot_psd,
                "color": normalized.get("color"),
                "line_style": normalize_line_style(normalized.get("line_style", "dashed")),
                "source": normalized.get("source", "imported"),
                "builtin_id": normalized.get("builtin_id"),
            }
        )

    return prepared


def normalize_line_style(line_style: Any) -> str:
    """Normalize line style naming to values usable by Matplotlib."""
    style = str(line_style).strip().lower()
    mapping = {
        "--": "--",
        "dashed": "--",
        "dash": "--",
        "-": "-",
        "solid": "-",
        ":": ":",
        "dot": ":",
        "dotted": ":",
        "-.": "-.",
        "dashdot": "-.",
        "dash-dot": "-.",
    }
    return mapping.get(style, "--")
