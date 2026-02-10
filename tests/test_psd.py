"""
Test suite for PSD (Power Spectral Density) calculation functions.

This module contains unit tests for the PSD calculation functions to ensure
accuracy and reliability. Tests include validation against known signals and
edge cases.

Author: SpectralEdge Development Team
"""

import unittest
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_almost_equal
from spectral_edge.core.psd import (
    calculate_psd_welch, calculate_psd_maximax, psd_to_db,
    calculate_rms_from_psd, get_window_options
)


class TestPSDCalculation(unittest.TestCase):
    """Test cases for PSD calculation functions."""
    
    def setUp(self):
        """
        Set up test fixtures before each test method.
        
        Creates test signals with known properties for validation.
        """
        # Test parameters
        self.sample_rate = 1000.0  # 1000 Hz
        self.duration = 10.0  # 10 seconds
        self.num_samples = int(self.sample_rate * self.duration)
        
        # Create time array
        self.time = np.linspace(0, self.duration, self.num_samples)
        
        # Test signal 1: Pure sine wave at 10 Hz
        self.freq_1 = 10.0
        self.amplitude_1 = 1.0
        self.signal_1 = self.amplitude_1 * np.sin(2 * np.pi * self.freq_1 * self.time)
        
        # Test signal 2: Two sine waves (10 Hz and 50 Hz)
        self.freq_2a = 10.0
        self.freq_2b = 50.0
        self.amplitude_2a = 1.0
        self.amplitude_2b = 0.5
        self.signal_2 = (self.amplitude_2a * np.sin(2 * np.pi * self.freq_2a * self.time) +
                        self.amplitude_2b * np.sin(2 * np.pi * self.freq_2b * self.time))
    
    def test_psd_basic_calculation(self):
        """
        Test basic PSD calculation on a simple sine wave.
        
        Verifies that the PSD function runs without errors and returns
        arrays of the expected shape.
        """
        frequencies, psd = calculate_psd_welch(self.signal_1, self.sample_rate)
        
        # Check that outputs are numpy arrays
        self.assertIsInstance(frequencies, np.ndarray)
        self.assertIsInstance(psd, np.ndarray)
        
        # Check that arrays have the same length
        self.assertEqual(len(frequencies), len(psd))
        
        # Check that frequencies are positive and increasing
        self.assertTrue(np.all(frequencies >= 0))
        self.assertTrue(np.all(np.diff(frequencies) > 0))
        
        # Check that PSD values are non-negative
        self.assertTrue(np.all(psd >= 0))
    
    def test_psd_peak_detection(self):
        """
        Test that PSD correctly identifies the peak frequency.
        
        For a pure sine wave, the PSD should have a clear peak at the
        signal frequency.
        """
        frequencies, psd = calculate_psd_welch(
            self.signal_1, 
            self.sample_rate,
            nperseg=512
        )
        
        # Find the frequency with maximum PSD
        peak_idx = np.argmax(psd)
        peak_frequency = frequencies[peak_idx]
        
        # The peak should be close to the signal frequency (10 Hz)
        # Allow 1 Hz tolerance due to frequency resolution
        self.assertAlmostEqual(peak_frequency, self.freq_1, delta=1.0)
    
    def test_psd_multiple_peaks(self):
        """
        Test PSD with a signal containing multiple frequency components.
        
        Verifies that PSD can identify multiple peaks in the spectrum.
        """
        frequencies, psd = calculate_psd_welch(
            self.signal_2,
            self.sample_rate,
            nperseg=512
        )
        
        # Find peaks in the PSD
        # We'll look for local maxima in specific frequency ranges
        
        # Peak 1: around 10 Hz
        mask_1 = (frequencies >= 8) & (frequencies <= 12)
        peak_1_idx = np.argmax(psd[mask_1])
        peak_1_freq = frequencies[mask_1][peak_1_idx]
        
        # Peak 2: around 50 Hz
        mask_2 = (frequencies >= 48) & (frequencies <= 52)
        peak_2_idx = np.argmax(psd[mask_2])
        peak_2_freq = frequencies[mask_2][peak_2_idx]
        
        # Verify peaks are close to expected frequencies
        self.assertAlmostEqual(peak_1_freq, self.freq_2a, delta=1.0)
        self.assertAlmostEqual(peak_2_freq, self.freq_2b, delta=1.0)
    
    def test_psd_window_types(self):
        """
        Test that different window types produce valid results.
        
        All window types should produce non-negative PSD values.
        """
        window_types = ['hann', 'hamming', 'blackman', 'bartlett', 'boxcar']
        
        for window in window_types:
            with self.subTest(window=window):
                frequencies, psd = calculate_psd_welch(
                    self.signal_1,
                    self.sample_rate,
                    window=window
                )
                
                # Check that PSD is non-negative
                self.assertTrue(np.all(psd >= 0))
                
                # Check that there is a peak near the signal frequency
                peak_idx = np.argmax(psd)
                peak_freq = frequencies[peak_idx]
                self.assertAlmostEqual(peak_freq, self.freq_1, delta=2.0)
    
    def test_psd_multi_channel(self):
        """
        Test PSD calculation with multi-channel data.
        
        Verifies that the function correctly handles 2D input arrays.
        """
        # Create multi-channel data (3 channels)
        signal_multi = np.array([
            self.signal_1,
            self.signal_2,
            self.signal_1 * 0.5
        ])
        
        frequencies, psd = calculate_psd_welch(signal_multi, self.sample_rate)
        
        # Check output shape
        self.assertEqual(psd.shape[0], 3)  # 3 channels
        self.assertEqual(psd.shape[1], len(frequencies))
        
        # Check that all channels have non-negative PSD
        self.assertTrue(np.all(psd >= 0))
    
    def test_psd_to_db_conversion(self):
        """
        Test conversion of PSD to decibel scale.
        
        Verifies the dB conversion formula.
        """
        # Create test PSD values
        psd_linear = np.array([1.0, 10.0, 100.0, 1000.0])
        
        # Convert to dB
        psd_db = psd_to_db(psd_linear, reference=1.0)
        
        # Expected dB values
        expected_db = np.array([0.0, 10.0, 20.0, 30.0])
        
        # Check that conversion is correct
        assert_array_almost_equal(psd_db, expected_db, decimal=5)
    
    def test_psd_to_db_with_zeros(self):
        """
        Test that dB conversion handles zero values gracefully.
        
        Zero values should not cause errors or inf values.
        """
        psd_with_zeros = np.array([0.0, 1.0, 10.0])
        
        # This should not raise an error
        psd_db = psd_to_db(psd_with_zeros)
        
        # Check that result is finite
        self.assertTrue(np.all(np.isfinite(psd_db)))
    
    def test_rms_calculation(self):
        """
        Test RMS calculation from PSD.
        
        For a sine wave with amplitude A, the RMS should be A/sqrt(2).
        """
        # Calculate PSD
        frequencies, psd = calculate_psd_welch(
            self.signal_1,
            self.sample_rate,
            nperseg=1024
        )
        
        # Calculate RMS from PSD
        rms = calculate_rms_from_psd(frequencies, psd)
        
        # Expected RMS for sine wave with amplitude 1.0
        expected_rms = self.amplitude_1 / np.sqrt(2)
        
        # Check that RMS is close to expected value
        # Allow 5% tolerance due to numerical approximations
        self.assertAlmostEqual(rms, expected_rms, delta=0.05 * expected_rms)
    
    def test_rms_with_frequency_range(self):
        """
        Test RMS calculation over a specific frequency range.
        
        Verifies that frequency range filtering works correctly.
        """
        frequencies, psd = calculate_psd_welch(
            self.signal_2,
            self.sample_rate,
            nperseg=1024
        )
        
        # Calculate RMS over a range that includes only the 10 Hz component
        rms_low = calculate_rms_from_psd(frequencies, psd, freq_min=5, freq_max=20)

        # Calculate RMS over a range that includes only the 50 Hz component
        rms_high = calculate_rms_from_psd(frequencies, psd, freq_min=40, freq_max=60)
        
        # Both should be positive and finite
        self.assertTrue(rms_low > 0)
        self.assertTrue(rms_high > 0)
        self.assertTrue(np.isfinite(rms_low))
        self.assertTrue(np.isfinite(rms_high))
    
    def test_window_options_function(self):
        """
        Test that get_window_options returns valid window types.
        """
        options = get_window_options()
        
        # Check that it returns a dictionary
        self.assertIsInstance(options, dict)
        
        # Check that it contains expected window types
        expected_windows = ['hann', 'hamming', 'blackman', 'bartlett', 'boxcar']
        for window in expected_windows:
            self.assertIn(window, options)
    
    def test_psd_input_validation(self):
        """
        Test that PSD function properly validates inputs.
        
        Should raise appropriate errors for invalid inputs.
        """
        # Test with empty array
        with self.assertRaises(ValueError):
            calculate_psd_welch(np.array([]), self.sample_rate)
        
        # Test with negative sample rate
        with self.assertRaises(ValueError):
            calculate_psd_welch(self.signal_1, -1000.0)
        
        # Test with zero sample rate
        with self.assertRaises(ValueError):
            calculate_psd_welch(self.signal_1, 0.0)


class TestWelchPSDKnownResults(unittest.TestCase):
    """
    Test Welch PSD calculation against known analytical results.

    These tests verify that the PSD implementation produces mathematically
    correct results using signals with known spectral properties.
    """

    def test_parseval_theorem_sinusoid(self):
        """
        Verify Parseval's theorem: integral of PSD equals signal variance.

        For a sinusoid A*sin(2*pi*f*t), the theoretical variance is A^2/2.
        The integral of the PSD over all frequencies should equal this variance.
        """
        # Create a pure sinusoid
        sample_rate = 1000.0
        duration = 20.0  # Long duration for accurate integration
        t = np.arange(0, duration, 1/sample_rate)
        amplitude = 2.5
        frequency = 50.0
        signal = amplitude * np.sin(2 * np.pi * frequency * t)

        # Calculate PSD with good frequency resolution
        frequencies, psd = calculate_psd_welch(
            signal, sample_rate, df=1.0, window='hann'
        )

        # Integrate PSD to get variance (Parseval's theorem)
        try:
            psd_integral = np.trapezoid(psd, frequencies)
        except AttributeError:
            psd_integral = np.trapz(psd, frequencies)

        # Theoretical variance for sinusoid: A^2 / 2
        theoretical_variance = amplitude**2 / 2

        # Allow 5% tolerance due to windowing effects
        self.assertAlmostEqual(
            psd_integral, theoretical_variance,
            delta=0.05 * theoretical_variance,
            msg=f"PSD integral ({psd_integral:.6f}) should equal "
                f"theoretical variance ({theoretical_variance:.6f})"
        )

    def test_parseval_theorem_two_sinusoids(self):
        """
        Verify Parseval's theorem for sum of two sinusoids.

        For signal A1*sin(f1*t) + A2*sin(f2*t), variance = (A1^2 + A2^2) / 2.
        """
        sample_rate = 2000.0
        duration = 30.0
        t = np.arange(0, duration, 1/sample_rate)

        # Two sinusoids with different amplitudes and frequencies
        A1, f1 = 1.5, 100.0
        A2, f2 = 0.8, 300.0
        signal = A1 * np.sin(2 * np.pi * f1 * t) + A2 * np.sin(2 * np.pi * f2 * t)

        frequencies, psd = calculate_psd_welch(signal, sample_rate, df=1.0)

        try:
            psd_integral = np.trapezoid(psd, frequencies)
        except AttributeError:
            psd_integral = np.trapz(psd, frequencies)

        # Theoretical variance for sum of uncorrelated sinusoids
        theoretical_variance = (A1**2 + A2**2) / 2

        self.assertAlmostEqual(
            psd_integral, theoretical_variance,
            delta=0.05 * theoretical_variance,
            msg=f"PSD integral for two sinusoids should match theoretical variance"
        )

    def test_rms_from_psd_matches_time_domain(self):
        """
        Verify RMS calculated from PSD matches time-domain RMS calculation.
        """
        sample_rate = 1000.0
        duration = 10.0
        t = np.arange(0, duration, 1/sample_rate)

        # Create a multi-tone signal
        signal = (1.0 * np.sin(2 * np.pi * 25 * t) +
                  0.5 * np.sin(2 * np.pi * 75 * t) +
                  0.3 * np.sin(2 * np.pi * 150 * t))

        # Calculate RMS directly from time domain
        rms_time_domain = np.sqrt(np.mean(signal**2))

        # Calculate RMS from PSD
        frequencies, psd = calculate_psd_welch(signal, sample_rate, df=1.0)
        rms_from_psd = calculate_rms_from_psd(frequencies, psd)

        # Should match within 3%
        self.assertAlmostEqual(
            rms_from_psd, rms_time_domain,
            delta=0.03 * rms_time_domain,
            msg=f"RMS from PSD ({rms_from_psd:.6f}) should match "
                f"time-domain RMS ({rms_time_domain:.6f})"
        )

    def test_white_noise_flat_spectrum(self):
        """
        Verify that white noise produces approximately flat PSD.

        White noise should have constant PSD across all frequencies.
        The variance of PSD values should be relatively low compared to mean.
        """
        np.random.seed(42)  # For reproducibility
        sample_rate = 1000.0
        duration = 60.0  # Long duration for good statistics

        # Generate white Gaussian noise
        noise_std = 1.0
        signal = np.random.randn(int(sample_rate * duration)) * noise_std

        frequencies, psd = calculate_psd_welch(
            signal, sample_rate, df=1.0, window='hann'
        )

        # Exclude DC component and very high frequencies
        mask = (frequencies > 5) & (frequencies < 450)
        psd_mid = psd[mask]

        # Mean PSD level for white noise: variance / (fs/2) = std^2 / (fs/2)
        # For density scaling: PSD ≈ variance * 2 / fs
        expected_psd_level = noise_std**2 * 2 / sample_rate
        mean_psd = np.mean(psd_mid)

        # Check mean is approximately correct (within 20%)
        self.assertAlmostEqual(
            mean_psd, expected_psd_level,
            delta=0.2 * expected_psd_level,
            msg="White noise PSD mean should match theoretical level"
        )

        # Check spectrum is relatively flat (coefficient of variation < 0.5)
        cv = np.std(psd_mid) / np.mean(psd_mid)
        self.assertLess(
            cv, 0.5,
            msg=f"White noise PSD should be relatively flat, CV={cv:.3f}"
        )

    def test_sinusoid_peak_power(self):
        """
        Verify that sinusoid peak power matches theoretical prediction.

        For a sinusoid, integrating the PSD peak should give A^2/2.
        """
        sample_rate = 1000.0
        duration = 20.0
        t = np.arange(0, duration, 1/sample_rate)

        amplitude = 3.0
        frequency = 100.0
        signal = amplitude * np.sin(2 * np.pi * frequency * t)

        # Use fine frequency resolution to capture the peak well
        df = 0.5
        frequencies, psd = calculate_psd_welch(signal, sample_rate, df=df)

        # Integrate around the peak (±5 Hz window)
        peak_mask = (frequencies >= frequency - 5) & (frequencies <= frequency + 5)
        try:
            peak_power = np.trapezoid(psd[peak_mask], frequencies[peak_mask])
        except AttributeError:
            peak_power = np.trapz(psd[peak_mask], frequencies[peak_mask])

        theoretical_power = amplitude**2 / 2

        self.assertAlmostEqual(
            peak_power, theoretical_power,
            delta=0.05 * theoretical_power,
            msg=f"Sinusoid peak power ({peak_power:.6f}) should match "
                f"theoretical ({theoretical_power:.6f})"
        )


class TestMaximaxPSDKnownResults(unittest.TestCase):
    """
    Test Maximax PSD calculation against known results.

    Maximax PSD takes the maximum PSD at each frequency across overlapping
    time windows, producing a conservative envelope spectrum.
    """

    def test_maximax_stationary_signal(self):
        """
        For a stationary signal, maximax PSD should be close to Welch average.

        With enough windows and overlap, the maximax of a stationary signal
        should not differ dramatically from the average.
        """
        sample_rate = 1000.0
        duration = 30.0  # Long enough for multiple 1-second windows
        t = np.arange(0, duration, 1/sample_rate)

        amplitude = 2.0
        frequency = 50.0
        signal = amplitude * np.sin(2 * np.pi * frequency * t)

        # Calculate both PSDs
        freq_welch, psd_welch = calculate_psd_welch(signal, sample_rate, df=1.0)
        freq_max, psd_max = calculate_psd_maximax(
            signal, sample_rate,
            maximax_window=1.0, overlap_percent=50.0, df=1.0
        )

        # For stationary signal, maximax should be >= welch at all frequencies
        # Use common frequency points
        min_len = min(len(psd_welch), len(psd_max))
        for i in range(min_len):
            self.assertGreaterEqual(
                psd_max[i], psd_welch[i] * 0.95,  # Allow 5% tolerance
                msg=f"Maximax PSD should be >= Welch PSD at freq {freq_max[i]:.1f} Hz"
            )

    def test_maximax_captures_transient(self):
        """
        Verify that maximax PSD captures transient events that averaging misses.

        A short transient should appear more prominently in maximax than in
        averaged PSD.
        """
        sample_rate = 1000.0
        duration = 30.0
        t = np.arange(0, duration, 1/sample_rate)

        # Background: low-amplitude 25 Hz signal
        signal = 0.5 * np.sin(2 * np.pi * 25 * t)

        # Add transient burst at t=15s: strong 200 Hz for 0.5 seconds
        transient_mask = (t >= 15) & (t < 15.5)
        signal[transient_mask] += 5.0 * np.sin(2 * np.pi * 200 * t[transient_mask])

        # Calculate PSDs
        freq_welch, psd_welch = calculate_psd_welch(signal, sample_rate, df=2.0)
        freq_max, psd_max = calculate_psd_maximax(
            signal, sample_rate,
            maximax_window=1.0, overlap_percent=50.0, df=2.0
        )

        # Find power at 200 Hz (transient frequency)
        idx_200_welch = np.argmin(np.abs(freq_welch - 200))
        idx_200_max = np.argmin(np.abs(freq_max - 200))

        power_welch_200 = psd_welch[idx_200_welch]
        power_max_200 = psd_max[idx_200_max]

        # Maximax should capture transient better (higher power at 200 Hz)
        self.assertGreater(
            power_max_200, power_welch_200,
            msg="Maximax should capture transient better than Welch average"
        )

        # The ratio should be significant (transient is only in ~0.5s of 30s)
        ratio = power_max_200 / power_welch_200
        self.assertGreater(
            ratio, 2.0,
            msg=f"Maximax/Welch ratio at transient freq should be > 2.0, got {ratio:.2f}"
        )

    def test_maximax_rms_conservation(self):
        """
        Verify RMS from maximax PSD is reasonable compared to time-domain.

        Maximax RMS should be >= time-domain RMS since it's an envelope.
        """
        sample_rate = 1000.0
        duration = 20.0
        t = np.arange(0, duration, 1/sample_rate)

        signal = 1.5 * np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 120 * t)

        # Time-domain RMS
        rms_time = np.sqrt(np.mean(signal**2))

        # Maximax PSD RMS
        frequencies, psd_max = calculate_psd_maximax(
            signal, sample_rate,
            maximax_window=1.0, overlap_percent=50.0, df=1.0
        )
        rms_maximax = calculate_rms_from_psd(frequencies, psd_max)

        # Maximax RMS should be close to (but typically >= ) time-domain RMS
        # Allow it to be slightly lower due to window edge effects
        self.assertGreater(
            rms_maximax, rms_time * 0.9,
            msg=f"Maximax RMS ({rms_maximax:.4f}) should be close to "
                f"time-domain RMS ({rms_time:.4f})"
        )

    def test_maximax_window_effect(self):
        """
        Verify that different maximax window sizes affect results appropriately.

        Shorter windows should capture faster transients better.
        """
        sample_rate = 1000.0
        duration = 20.0
        t = np.arange(0, duration, 1/sample_rate)

        # Signal with brief transient
        signal = 0.3 * np.sin(2 * np.pi * 30 * t)

        # Very brief transient (0.1 second)
        transient_mask = (t >= 10) & (t < 10.1)
        signal[transient_mask] += 4.0 * np.sin(2 * np.pi * 150 * t[transient_mask])

        # Compare 0.5s and 2.0s windows
        _, psd_short = calculate_psd_maximax(
            signal, sample_rate, maximax_window=0.5, overlap_percent=50.0
        )
        _, psd_long = calculate_psd_maximax(
            signal, sample_rate, maximax_window=2.0, overlap_percent=50.0
        )

        # Shorter window should capture the brief transient better
        # (higher overall peak or higher values near transient frequency)
        max_short = np.max(psd_short)
        max_long = np.max(psd_long)

        # Short window should have higher or equal max (captures transient)
        self.assertGreaterEqual(
            max_short * 1.1, max_long,  # Allow 10% tolerance
            msg="Shorter maximax window should capture brief transients better"
        )

    def test_maximax_parseval_bounds(self):
        """
        Verify maximax PSD integral is bounded by theoretical values.

        For a stationary signal, maximax integral should be close to variance.
        """
        sample_rate = 1000.0
        duration = 30.0
        t = np.arange(0, duration, 1/sample_rate)

        amplitude = 2.0
        signal = amplitude * np.sin(2 * np.pi * 80 * t)

        frequencies, psd_max = calculate_psd_maximax(
            signal, sample_rate,
            maximax_window=1.0, overlap_percent=50.0, df=1.0
        )

        try:
            maximax_integral = np.trapezoid(psd_max, frequencies)
        except AttributeError:
            maximax_integral = np.trapz(psd_max, frequencies)

        theoretical_variance = amplitude**2 / 2

        # For stationary signal, should be close to variance
        self.assertAlmostEqual(
            maximax_integral, theoretical_variance,
            delta=0.15 * theoretical_variance,  # 15% tolerance
            msg=f"Maximax integral ({maximax_integral:.4f}) should be close to "
                f"theoretical variance ({theoretical_variance:.4f})"
        )


class TestPSDFrequencyResolution(unittest.TestCase):
    """
    Test that PSD frequency resolution (df) parameter works correctly.
    """

    def test_df_parameter_welch(self):
        """
        Verify that df parameter controls frequency resolution correctly.
        """
        sample_rate = 1000.0
        duration = 10.0
        signal = np.random.randn(int(sample_rate * duration))

        # Calculate with different df values
        df_values = [1.0, 2.0, 5.0]

        for df in df_values:
            frequencies, psd = calculate_psd_welch(signal, sample_rate, df=df)

            # Check actual frequency spacing
            actual_df = frequencies[1] - frequencies[0]

            # Actual df should be close to requested (may differ slightly due to nperseg rounding)
            self.assertAlmostEqual(
                actual_df, df,
                delta=df * 0.5,  # Within 50% of requested
                msg=f"Actual df ({actual_df:.2f}) should be close to requested ({df:.2f})"
            )

    def test_df_affects_peak_resolution(self):
        """
        Verify that finer df resolves closely spaced frequencies better.
        """
        sample_rate = 1000.0
        duration = 20.0
        t = np.arange(0, duration, 1/sample_rate)

        # Two closely spaced frequencies (5 Hz apart)
        f1, f2 = 100.0, 105.0
        signal = np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t)

        # Coarse resolution (df=10 Hz) - should NOT resolve the peaks
        freq_coarse, psd_coarse = calculate_psd_welch(signal, sample_rate, df=10.0)

        # Fine resolution (df=1 Hz) - should resolve the peaks
        freq_fine, psd_fine = calculate_psd_welch(signal, sample_rate, df=1.0)

        # Count peaks in the 90-115 Hz range
        mask_coarse = (freq_coarse >= 90) & (freq_coarse <= 115)
        mask_fine = (freq_fine >= 90) & (freq_fine <= 115)

        # Fine resolution should have more data points
        self.assertGreater(
            np.sum(mask_fine), np.sum(mask_coarse),
            msg="Finer df should have more frequency points"
        )


if __name__ == '__main__':
    # Run all tests when this file is executed directly
    unittest.main()
