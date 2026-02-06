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
    spacing = getattr(psd_config, "frequency_spacing", "constant_bandwidth")
    if spacing == "constant_bandwidth":
        return frequencies, psd

    octave_fraction = None
    if hasattr(psd_config, "get_octave_fraction"):
        octave_fraction = psd_config.get_octave_fraction()

    if octave_fraction is None:
        logger.warning(f"Unknown frequency spacing '{spacing}', using narrowband output")
        return frequencies, psd

    try:
        freq_min = getattr(psd_config, "freq_min", None)
        freq_max = getattr(psd_config, "freq_max", None)
        if freq_min is None or freq_max is None:
            freq_min = float(frequencies[0])
            freq_max = float(frequencies[-1])

        return convert_psd_to_octave_bands(
            frequencies,
            psd,
            octave_fraction=octave_fraction,
            freq_min=freq_min,
            freq_max=freq_max
        )
    except Exception as exc:
        logger.warning(f"Failed to apply octave spacing ({spacing}): {exc}")
        return frequencies, psd
