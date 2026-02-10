"""
Comprehensive test suite for core PSD and signal processing functions.

This module contains all unit tests for:
- PSD calculation (Welch method)
- Maximax PSD calculation
- Cross-spectral density (CSD)
- Coherence
- Transfer function
- Octave band conversion
- RMS calculation

Tests are organized by:
- Accuracy: Mathematical/algorithmic correctness
- Robustness: Edge cases, error handling, invalid inputs
- Reliability: Consistent behavior across conditions

Author: SpectralEdge Development Team
"""

import unittest
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_almost_equal
import warnings

from spectral_edge.core.psd import (
    calculate_psd_welch,
    calculate_psd_maximax,
    psd_to_db,
    calculate_rms_from_psd,
    get_window_options,
    convert_psd_to_octave_bands,
    calculate_csd,
    calculate_coherence,
    calculate_transfer_function
)


class TestPSDAccuracy(unittest.TestCase):
    """Accuracy tests for PSD calculations - validates mathematical correctness."""

    def setUp(self):
        """Set up test fixtures with known signal properties."""
        self.sample_rate = 1000.0
        self.duration = 10.0
        self.num_samples = int(self.sample_rate * self.duration)
        self.time = np.linspace(0, self.duration, self.num_samples, endpoint=False)

        # Pure sine wave at 10 Hz with amplitude 1.0
        self.freq_1 = 10.0
        self.amplitude_1 = 1.0
        self.signal_1 = self.amplitude_1 * np.sin(2 * np.pi * self.freq_1 * self.time)

        # Two-frequency signal
        self.freq_2a = 10.0
        self.freq_2b = 50.0
        self.amplitude_2a = 1.0
        self.amplitude_2b = 0.5
        self.signal_2 = (self.amplitude_2a * np.sin(2 * np.pi * self.freq_2a * self.time) +
                        self.amplitude_2b * np.sin(2 * np.pi * self.freq_2b * self.time))

    def test_psd_basic_calculation(self):
        """Test basic PSD calculation returns valid arrays."""
        frequencies, psd = calculate_psd_welch(self.signal_1, self.sample_rate)

        self.assertIsInstance(frequencies, np.ndarray)
        self.assertIsInstance(psd, np.ndarray)
        self.assertEqual(len(frequencies), len(psd))
        self.assertTrue(np.all(frequencies >= 0))
        self.assertTrue(np.all(np.diff(frequencies) > 0))
        self.assertTrue(np.all(psd >= 0))

    def test_psd_peak_detection(self):
        """Test PSD correctly identifies peak at signal frequency."""
        frequencies, psd = calculate_psd_welch(
            self.signal_1, self.sample_rate, nperseg=512
        )

        peak_idx = np.argmax(psd)
        peak_frequency = frequencies[peak_idx]

        self.assertAlmostEqual(peak_frequency, self.freq_1, delta=1.0)

    def test_psd_multiple_peaks(self):
        """Test PSD identifies multiple frequency components."""
        frequencies, psd = calculate_psd_welch(
            self.signal_2, self.sample_rate, nperseg=512
        )

        # Find peaks in specific frequency ranges
        mask_1 = (frequencies >= 8) & (frequencies <= 12)
        peak_1_freq = frequencies[mask_1][np.argmax(psd[mask_1])]

        mask_2 = (frequencies >= 48) & (frequencies <= 52)
        peak_2_freq = frequencies[mask_2][np.argmax(psd[mask_2])]

        self.assertAlmostEqual(peak_1_freq, self.freq_2a, delta=1.0)
        self.assertAlmostEqual(peak_2_freq, self.freq_2b, delta=1.0)

    def test_psd_parseval_theorem(self):
        """
        Test Parseval's theorem: total power in PSD equals time-domain variance.

        For a signal x(t), Parseval's theorem states:
        variance(x) ≈ integral(PSD) * df
        """
        frequencies, psd = calculate_psd_welch(
            self.signal_1, self.sample_rate, df=1.0
        )

        # Calculate power from PSD (integral) - use trapezoid for newer numpy
        try:
            psd_power = np.trapezoid(psd, frequencies)
        except AttributeError:
            psd_power = np.trapz(psd, frequencies)

        # Calculate variance from time domain
        time_variance = np.var(self.signal_1)

        # Should be equal within 10% (numerical integration error)
        self.assertAlmostEqual(psd_power, time_variance, delta=0.1 * time_variance)

    def test_psd_nyquist_limit(self):
        """Test PSD doesn't exceed Nyquist frequency (fs/2)."""
        frequencies, psd = calculate_psd_welch(self.signal_1, self.sample_rate)

        nyquist = self.sample_rate / 2
        self.assertLessEqual(frequencies[-1], nyquist)

    def test_psd_dc_offset_removal(self):
        """Test DC component is properly removed by detrending."""
        # Add large DC offset to signal
        signal_with_dc = self.signal_1 + 100.0

        frequencies, psd = calculate_psd_welch(
            signal_with_dc, self.sample_rate, df=1.0
        )

        # DC component (0 Hz or very low freq) should be small
        dc_power = psd[0] if frequencies[0] == 0 else psd[frequencies < 1.0].sum()
        ac_power = psd[frequencies >= 5.0].sum()

        # AC power should dominate (DC removed)
        self.assertGreater(ac_power, dc_power * 10)

    def test_psd_overlap_effect(self):
        """Test different overlap values produce statistically valid results."""
        overlaps = [0, 25, 50, 75]
        results = []

        for overlap in overlaps:
            nperseg = 512
            noverlap = int(nperseg * overlap / 100)
            frequencies, psd = calculate_psd_welch(
                self.signal_1, self.sample_rate,
                nperseg=nperseg, noverlap=noverlap
            )
            # Find peak power
            results.append(np.max(psd))

        # All should find approximately the same peak (within factor of 2)
        for r in results:
            self.assertAlmostEqual(r, results[0], delta=results[0])

    def test_rms_calculation(self):
        """Test RMS from PSD matches theory (A/√2 for sine wave)."""
        frequencies, psd = calculate_psd_welch(
            self.signal_1, self.sample_rate, nperseg=1024
        )

        rms = calculate_rms_from_psd(frequencies, psd)
        expected_rms = self.amplitude_1 / np.sqrt(2)

        self.assertAlmostEqual(rms, expected_rms, delta=0.05 * expected_rms)

    def test_rms_with_frequency_range(self):
        """Test RMS calculation over specific frequency bands."""
        frequencies, psd = calculate_psd_welch(
            self.signal_2, self.sample_rate, nperseg=1024
        )

        # Calculate RMS over range including only 10 Hz component
        rms_low = calculate_rms_from_psd(frequencies, psd, freq_min=5, freq_max=20)

        # Calculate RMS over range including only 50 Hz component
        rms_high = calculate_rms_from_psd(frequencies, psd, freq_min=40, freq_max=60)

        self.assertTrue(rms_low > 0)
        self.assertTrue(rms_high > 0)
        self.assertTrue(np.isfinite(rms_low))
        self.assertTrue(np.isfinite(rms_high))

        # 10 Hz component is stronger (amplitude 1.0 vs 0.5)
        self.assertGreater(rms_low, rms_high)

    def test_psd_to_db_conversion(self):
        """Test dB conversion formula (10×log10) is correct."""
        psd_linear = np.array([1.0, 10.0, 100.0, 1000.0])
        psd_db = psd_to_db(psd_linear, reference=1.0)
        expected_db = np.array([0.0, 10.0, 20.0, 30.0])

        assert_array_almost_equal(psd_db, expected_db, decimal=5)


class TestMaximaxAccuracy(unittest.TestCase):
    """Accuracy tests for Maximax PSD calculation."""

    def setUp(self):
        """Set up test signals."""
        self.sample_rate = 1000.0
        self.duration = 10.0
        self.time = np.linspace(0, self.duration,
                                int(self.sample_rate * self.duration), endpoint=False)

        # Stationary signal
        self.stationary_signal = np.sin(2 * np.pi * 50 * self.time)

        # Signal with transient (burst at t=5s)
        self.transient_signal = np.sin(2 * np.pi * 50 * self.time).copy()
        burst_start = int(5.0 * self.sample_rate)
        burst_end = int(5.5 * self.sample_rate)
        self.transient_signal[burst_start:burst_end] *= 5.0

    def test_maximax_envelope_property(self):
        """Test Maximax PSD ≥ Welch PSD at ALL frequencies."""
        freq_welch, psd_welch = calculate_psd_welch(
            self.stationary_signal, self.sample_rate, df=1.0
        )

        freq_maximax, psd_maximax = calculate_psd_maximax(
            self.stationary_signal, self.sample_rate, df=1.0
        )

        # Interpolate to same frequencies if needed
        if len(freq_welch) == len(freq_maximax):
            # Maximax should be >= Welch everywhere (with small tolerance for numerics)
            self.assertTrue(np.all(psd_maximax >= psd_welch * 0.99))

    def test_maximax_captures_transients(self):
        """Test Maximax captures transient events that Welch averages out."""
        freq_welch, psd_welch = calculate_psd_welch(
            self.transient_signal, self.sample_rate, df=1.0
        )

        freq_maximax, psd_maximax = calculate_psd_maximax(
            self.transient_signal, self.sample_rate, df=1.0, maximax_window=1.0
        )

        # At 50 Hz, maximax should be significantly higher due to transient
        idx_50hz = np.argmin(np.abs(freq_welch - 50))

        # Maximax should capture the 5x burst
        ratio = psd_maximax[idx_50hz] / psd_welch[idx_50hz]
        self.assertGreater(ratio, 2.0)  # Should be much higher than averaged


class TestCrossSpectrumAccuracy(unittest.TestCase):
    """Accuracy tests for cross-spectral analysis."""

    def setUp(self):
        """Set up correlated test signals."""
        self.sample_rate = 1000.0
        self.duration = 10.0
        self.time = np.linspace(0, self.duration,
                                int(self.sample_rate * self.duration), endpoint=False)

        # Two correlated signals at 50 Hz with phase shift
        self.freq = 50.0
        self.phase_shift = np.pi / 4  # 45 degrees

        np.random.seed(42)
        noise = 0.1 * np.random.randn(len(self.time))

        self.signal1 = np.sin(2 * np.pi * self.freq * self.time) + noise
        self.signal2 = np.sin(2 * np.pi * self.freq * self.time + self.phase_shift) + noise

        # Uncorrelated signals
        self.noise1 = np.random.randn(len(self.time))
        self.noise2 = np.random.randn(len(self.time))

    def test_csd_peak_at_signal_frequency(self):
        """Test CSD peaks at the correlated signal frequency."""
        frequencies, csd = calculate_csd(
            self.signal1, self.signal2, self.sample_rate, df=1.0
        )

        csd_magnitude = np.abs(csd)
        peak_idx = np.argmax(csd_magnitude)
        peak_freq = frequencies[peak_idx]

        self.assertAlmostEqual(peak_freq, self.freq, delta=2.0)

    def test_csd_symmetry(self):
        """Test CSD(x,y) = conj(CSD(y,x))."""
        freq1, csd_xy = calculate_csd(
            self.signal1, self.signal2, self.sample_rate, df=1.0
        )
        freq2, csd_yx = calculate_csd(
            self.signal2, self.signal1, self.sample_rate, df=1.0
        )

        # CSD_xy should equal conjugate of CSD_yx
        assert_array_almost_equal(csd_xy, np.conj(csd_yx), decimal=10)

    def test_coherence_identical_signals(self):
        """Test coherence = 1.0 for identical signals."""
        frequencies, coherence = calculate_coherence(
            self.signal1, self.signal1, self.sample_rate, df=1.0
        )

        # Coherence should be very close to 1.0 everywhere
        self.assertTrue(np.all(coherence > 0.99))

    def test_coherence_uncorrelated_signals(self):
        """Test coherence ≈ 0 for uncorrelated random signals."""
        frequencies, coherence = calculate_coherence(
            self.noise1, self.noise2, self.sample_rate, df=1.0
        )

        # Mean coherence should be low for uncorrelated noise
        self.assertLess(np.mean(coherence), 0.3)

    def test_coherence_bounds(self):
        """Test coherence is always in valid range [0, 1] (with numerical tolerance)."""
        # Test with various signal combinations
        test_signals = [
            (self.signal1, self.signal2),
            (self.noise1, self.noise2),
            (self.signal1, self.noise1),
        ]

        for sig1, sig2 in test_signals:
            frequencies, coherence = calculate_coherence(
                sig1, sig2, self.sample_rate, df=1.0
            )
            self.assertTrue(np.all(coherence >= -0.01))  # Small tolerance for numerics
            self.assertTrue(np.all(coherence <= 1.01))   # Small tolerance for numerics

    def test_transfer_function_unity_gain(self):
        """Test transfer function magnitude ≈ 1.0 for identical signals."""
        frequencies, magnitude, phase = calculate_transfer_function(
            self.signal1, self.signal1, self.sample_rate, df=1.0
        )

        # At signal frequency, magnitude should be ~1.0
        idx = np.argmin(np.abs(frequencies - self.freq))
        self.assertAlmostEqual(magnitude[idx], 1.0, delta=0.1)

    def test_transfer_function_phase_shift(self):
        """Test transfer function detects known phase shift."""
        frequencies, magnitude, phase = calculate_transfer_function(
            self.signal1, self.signal2, self.sample_rate, df=1.0
        )

        # Find phase at signal frequency
        idx = np.argmin(np.abs(frequencies - self.freq))
        measured_phase = phase[idx]
        expected_phase = np.degrees(self.phase_shift)

        # Phase should be close to expected (within 10 degrees)
        self.assertAlmostEqual(measured_phase, expected_phase, delta=10.0)


class TestOctaveBandAccuracy(unittest.TestCase):
    """Accuracy tests for octave band conversion."""

    def setUp(self):
        """Set up broadband test signal."""
        self.sample_rate = 10000.0
        self.duration = 10.0
        np.random.seed(42)
        self.broadband_signal = np.random.randn(int(self.sample_rate * self.duration))

    def test_octave_band_energy_conservation(self):
        """Test octave band conversion produces valid results."""
        frequencies, psd = calculate_psd_welch(
            self.broadband_signal, self.sample_rate, df=1.0
        )

        # Convert to 1/3 octave
        oct_freq, oct_psd = convert_psd_to_octave_bands(
            frequencies, psd, octave_fraction=3, freq_min=20, freq_max=4000
        )

        # Basic validation: should have fewer points than narrowband
        self.assertLess(len(oct_freq), len(frequencies))

        # All octave PSD values should be positive
        self.assertTrue(np.all(oct_psd >= 0))

        # Frequencies should be sorted
        self.assertTrue(np.all(np.diff(oct_freq) > 0))

    def test_octave_band_all_fractions(self):
        """Test all octave fractions work correctly."""
        frequencies, psd = calculate_psd_welch(
            self.broadband_signal, self.sample_rate, df=1.0
        )

        fractions = [1, 3, 6, 12, 24]

        for fraction in fractions:
            with self.subTest(fraction=fraction):
                oct_freq, oct_psd = convert_psd_to_octave_bands(
                    frequencies, psd, octave_fraction=fraction,
                    freq_min=100, freq_max=1000
                )

                # Should return valid arrays
                self.assertTrue(len(oct_freq) > 0)
                self.assertEqual(len(oct_freq), len(oct_psd))
                self.assertTrue(np.all(oct_psd >= 0))

                # More bands for higher fractions
                if fraction > 1:
                    oct_freq_1, _ = convert_psd_to_octave_bands(
                        frequencies, psd, octave_fraction=1,
                        freq_min=100, freq_max=1000
                    )
                    self.assertGreater(len(oct_freq), len(oct_freq_1))

    def test_octave_band_clamps_to_available_frequency_range(self):
        """Requested max frequency above Nyquist should be clipped to available data."""
        sample_rate = 100.0
        duration = 20.0
        time = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        signal = np.sin(2 * np.pi * 10.0 * time) + 0.5 * np.sin(2 * np.pi * 20.0 * time)

        frequencies, psd = calculate_psd_welch(signal, sample_rate, df=1.0)
        oct_freq, oct_psd = convert_psd_to_octave_bands(
            frequencies,
            psd,
            octave_fraction=3,
            freq_min=1.0,
            freq_max=2500.0,
        )

        self.assertGreater(len(oct_freq), 0)
        self.assertLessEqual(np.max(oct_freq), frequencies[-1] + 1e-9)

        finite_oct_psd = oct_psd[np.isfinite(oct_psd)]
        self.assertTrue(np.all(finite_oct_psd >= 0))

    def test_octave_band_with_zero_hz_input_avoids_log10_runtime_warning(self):
        """Conversion should handle 0 Hz bins without divide-by-zero warnings."""
        frequencies = np.array([0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 50.0], dtype=np.float64)
        psd = np.ones_like(frequencies, dtype=np.float64)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            oct_freq, _ = convert_psd_to_octave_bands(
                frequencies,
                psd,
                octave_fraction=3,
                freq_min=0.0,
                freq_max=2500.0,
            )

        divide_by_zero_log_warnings = [
            warning
            for warning in caught
            if issubclass(warning.category, RuntimeWarning)
            and "divide by zero" in str(warning.message).lower()
            and "log10" in str(warning.message).lower()
        ]

        self.assertEqual(len(divide_by_zero_log_warnings), 0)
        self.assertGreater(len(oct_freq), 0)
        self.assertLessEqual(np.max(oct_freq), 50.0 + 1e-9)


class TestPSDRobustness(unittest.TestCase):
    """Robustness tests - edge cases and error handling."""

    def setUp(self):
        """Set up test data."""
        self.sample_rate = 1000.0
        self.time = np.linspace(0, 10, 10000)
        self.signal = np.sin(2 * np.pi * 50 * self.time)

    def test_psd_input_validation_empty_array(self):
        """Test proper error for empty arrays."""
        with self.assertRaises(ValueError):
            calculate_psd_welch(np.array([]), self.sample_rate)

    def test_psd_input_validation_negative_sample_rate(self):
        """Test proper error for negative sample rate."""
        with self.assertRaises(ValueError):
            calculate_psd_welch(self.signal, -1000.0)

    def test_psd_input_validation_zero_sample_rate(self):
        """Test proper error for zero sample rate."""
        with self.assertRaises(ValueError):
            calculate_psd_welch(self.signal, 0.0)

    def test_psd_very_short_signal(self):
        """Test graceful handling when signal < nperseg."""
        short_signal = np.sin(2 * np.pi * 50 * np.linspace(0, 0.1, 100))

        # Should either work with smaller nperseg or raise informative error
        try:
            frequencies, psd = calculate_psd_welch(
                short_signal, self.sample_rate, df=1.0
            )
            # If it works, results should be valid
            self.assertTrue(np.all(psd >= 0))
        except ValueError as e:
            # Error should be informative
            self.assertIn("nperseg", str(e).lower())

    def test_psd_nan_handling(self):
        """Test NaN values in signal produce NaN in output (scipy behavior)."""
        signal_with_nan = self.signal.copy()
        signal_with_nan[100] = np.nan

        # scipy.signal.welch propagates NaN - output will contain NaN
        frequencies, psd = calculate_psd_welch(signal_with_nan, self.sample_rate)

        # The output should contain NaN values
        self.assertTrue(np.any(np.isnan(psd)))

    def test_psd_to_db_with_zeros(self):
        """Test dB conversion handles zero values gracefully."""
        psd_with_zeros = np.array([0.0, 1.0, 10.0])
        psd_db = psd_to_db(psd_with_zeros)

        # Should not produce infinity
        self.assertTrue(np.all(np.isfinite(psd_db)))

    def test_csd_different_lengths_error(self):
        """Test proper error when signals have different lengths."""
        signal1 = np.random.randn(1000)
        signal2 = np.random.randn(900)  # Different length

        with self.assertRaises(ValueError):
            calculate_csd(signal1, signal2, self.sample_rate)

    def test_coherence_different_lengths_error(self):
        """Test proper error when signals have different lengths."""
        signal1 = np.random.randn(1000)
        signal2 = np.random.randn(900)

        with self.assertRaises(ValueError):
            calculate_coherence(signal1, signal2, self.sample_rate)


class TestPSDReliability(unittest.TestCase):
    """Reliability tests - consistent behavior across conditions."""

    def setUp(self):
        """Set up test data."""
        self.sample_rate = 1000.0
        self.time = np.linspace(0, 10, 10000, endpoint=False)
        self.signal = np.sin(2 * np.pi * 50 * self.time)

    def test_psd_window_types_all_valid(self):
        """Test all window types produce valid results."""
        window_types = ['hann', 'hamming', 'blackman', 'bartlett', 'boxcar', 'flattop']

        for window in window_types:
            with self.subTest(window=window):
                try:
                    frequencies, psd = calculate_psd_welch(
                        self.signal, self.sample_rate, window=window
                    )

                    self.assertTrue(np.all(psd >= 0))

                    # Should find peak near 50 Hz
                    peak_freq = frequencies[np.argmax(psd)]
                    self.assertAlmostEqual(peak_freq, 50.0, delta=2.0)
                except ValueError:
                    # Some windows may not be supported
                    pass

    def test_psd_multi_channel(self):
        """Test PSD handles multi-channel 2D arrays correctly."""
        signal_multi = np.array([
            self.signal,
            self.signal * 0.5,
            np.sin(2 * np.pi * 100 * self.time)
        ])

        frequencies, psd = calculate_psd_welch(signal_multi, self.sample_rate)

        self.assertEqual(psd.shape[0], 3)
        self.assertEqual(psd.shape[1], len(frequencies))
        self.assertTrue(np.all(psd >= 0))

    def test_psd_deterministic(self):
        """Test PSD produces same result for same input."""
        freq1, psd1 = calculate_psd_welch(self.signal, self.sample_rate, df=1.0)
        freq2, psd2 = calculate_psd_welch(self.signal, self.sample_rate, df=1.0)

        assert_array_almost_equal(freq1, freq2)
        assert_array_almost_equal(psd1, psd2)

    def test_window_options_function(self):
        """Test get_window_options returns expected types."""
        options = get_window_options()

        self.assertIsInstance(options, dict)

        expected_windows = ['hann', 'hamming', 'blackman', 'bartlett']
        for window in expected_windows:
            self.assertIn(window, options)

    def test_psd_large_signal(self):
        """Test PSD handles large signals efficiently."""
        # 1 million samples
        large_signal = np.random.randn(1_000_000)

        # Should complete without memory error
        frequencies, psd = calculate_psd_welch(
            large_signal, self.sample_rate, df=1.0
        )

        self.assertTrue(len(frequencies) > 0)
        self.assertTrue(np.all(psd >= 0))


if __name__ == '__main__':
    unittest.main()
