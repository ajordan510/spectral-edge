"""
PSD Output Utilities

Helpers for applying display spacing to PSD outputs.
"""

from typing import Tuple
import logging
import numpy as np

from spectral_edge.core.psd import convert_psd_to_octave_bands

logger = logging.getLogger(__name__)


def apply_frequency_spacing(
    frequencies: np.ndarray,
    psd: np.ndarray,
    psd_config
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply frequency spacing conversion for output/display.

    Parameters
    ----------
    frequencies : np.ndarray
        Narrowband frequency array.
    psd : np.ndarray
        Narrowband PSD array.
    psd_config : PSDConfig
        PSD configuration with spacing settings.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (frequencies_out, psd_out)
    """
    frequencies_arr = np.asarray(frequencies)
    psd_arr = np.asarray(psd)
    if frequencies_arr.size != psd_arr.size:
        common = min(frequencies_arr.size, psd_arr.size)
        frequencies_arr = frequencies_arr[:common]
        psd_arr = psd_arr[:common]
    if frequencies_arr.size == 0 or psd_arr.size == 0:
        return frequencies_arr, psd_arr

    spacing = getattr(psd_config, "frequency_spacing", "constant_bandwidth")
    freq_min = getattr(psd_config, "freq_min", None)
    freq_max = getattr(psd_config, "freq_max", None)
    try:
        freq_min = float(freq_min) if freq_min is not None else float(frequencies_arr[0])
    except (TypeError, ValueError):
        freq_min = float(frequencies_arr[0])
    try:
        freq_max = float(freq_max) if freq_max is not None else float(frequencies_arr[-1])
    except (TypeError, ValueError):
        freq_max = float(frequencies_arr[-1])

    if freq_min > freq_max:
        freq_min, freq_max = freq_max, freq_min

    if spacing == "constant_bandwidth":
        mask = (frequencies_arr >= freq_min) & (frequencies_arr <= freq_max)
        if not np.any(mask):
            return np.array([], dtype=frequencies_arr.dtype), np.array([], dtype=psd_arr.dtype)
        return frequencies_arr[mask], psd_arr[mask]

    octave_fraction = None
    if hasattr(psd_config, "get_octave_fraction"):
        octave_fraction = psd_config.get_octave_fraction()

    if octave_fraction is None:
        logger.warning(f"Unknown frequency spacing '{spacing}', using narrowband output")
        mask = (frequencies_arr >= freq_min) & (frequencies_arr <= freq_max)
        if not np.any(mask):
            return np.array([], dtype=frequencies_arr.dtype), np.array([], dtype=psd_arr.dtype)
        return frequencies_arr[mask], psd_arr[mask]

    try:
        return convert_psd_to_octave_bands(
            frequencies_arr,
            psd_arr,
            octave_fraction=octave_fraction,
            freq_min=freq_min,
            freq_max=freq_max
        )
    except Exception as exc:
        logger.warning(f"Failed to apply octave spacing ({spacing}): {exc}")
        mask = (frequencies_arr >= freq_min) & (frequencies_arr <= freq_max)
        if not np.any(mask):
            return np.array([], dtype=frequencies_arr.dtype), np.array([], dtype=psd_arr.dtype)
        return frequencies_arr[mask], psd_arr[mask]
