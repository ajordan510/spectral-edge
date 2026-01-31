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
    calculate_psd_welch, psd_to_db, calculate_rms_from_psd, get_window_options
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


if __name__ == '__main__':
    # Run all tests when this file is executed directly
    unittest.main()
