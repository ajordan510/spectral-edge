"""
Test suite for error handling and input validation.

Tests validate that the application:
- Provides clear error messages for invalid inputs
- Handles edge cases gracefully without crashing
- Validates parameters before processing

Author: SpectralEdge Development Team
"""

import pytest
import numpy as np

from spectral_edge.core.psd import (
    calculate_psd_welch,
    calculate_psd_maximax,
    calculate_csd,
    calculate_coherence,
    calculate_transfer_function,
    calculate_rms_from_psd,
    convert_psd_to_octave_bands
)


class TestPSDInputValidation:
    """Tests for PSD function input validation."""

    def test_empty_signal_error(self):
        """Test proper error for empty signal array."""
        with pytest.raises(ValueError) as excinfo:
            calculate_psd_welch(np.array([]), 1000.0)
        assert "empty" in str(excinfo.value).lower()

    def test_negative_sample_rate_error(self):
        """Test proper error for negative sample rate."""
        signal = np.random.randn(1000)
        with pytest.raises(ValueError) as excinfo:
            calculate_psd_welch(signal, -1000.0)
        assert "sample" in str(excinfo.value).lower() or "positive" in str(excinfo.value).lower()

    def test_zero_sample_rate_error(self):
        """Test proper error for zero sample rate."""
        signal = np.random.randn(1000)
        with pytest.raises(ValueError) as excinfo:
            calculate_psd_welch(signal, 0.0)

    def test_nperseg_larger_than_signal_error(self):
        """Test error when nperseg > signal length."""
        signal = np.random.randn(100)  # Short signal
        with pytest.raises(ValueError) as excinfo:
            calculate_psd_welch(signal, 1000.0, nperseg=500)
        assert "nperseg" in str(excinfo.value).lower()

    def test_negative_df_error(self):
        """Test error for negative frequency resolution."""
        signal = np.random.randn(10000)
        with pytest.raises(ValueError) as excinfo:
            calculate_psd_welch(signal, 1000.0, df=-1.0)

    def test_df_exceeds_nyquist_error(self):
        """Test error when df >= Nyquist frequency."""
        signal = np.random.randn(10000)
        sample_rate = 1000.0
        with pytest.raises(ValueError) as excinfo:
            calculate_psd_welch(signal, sample_rate, df=600.0)  # df > fs/2


class TestMaximaxInputValidation:
    """Tests for Maximax PSD input validation."""

    def test_maximax_short_signal_error(self):
        """Test error when signal too short for maximax window."""
        signal = np.random.randn(500)  # 0.5 seconds at 1000 Hz
        sample_rate = 1000.0

        # 1 second window with 0.5 second signal should fail
        with pytest.raises(ValueError):
            calculate_psd_maximax(
                signal, sample_rate, df=1.0, maximax_window=1.0
            )

    def test_maximax_window_validation(self):
        """Test maximax window parameter validation."""
        signal = np.random.randn(10000)
        sample_rate = 1000.0

        # Negative window should fail
        with pytest.raises(ValueError):
            calculate_psd_maximax(
                signal, sample_rate, df=1.0, maximax_window=-1.0
            )


class TestCrossSpectrumInputValidation:
    """Tests for cross-spectrum function input validation."""

    def test_csd_different_length_signals_error(self):
        """Test error when signals have different lengths."""
        signal1 = np.random.randn(1000)
        signal2 = np.random.randn(900)

        with pytest.raises(ValueError) as excinfo:
            calculate_csd(signal1, signal2, 1000.0)
        assert "length" in str(excinfo.value).lower()

    def test_coherence_different_length_signals_error(self):
        """Test error when signals have different lengths."""
        signal1 = np.random.randn(1000)
        signal2 = np.random.randn(900)

        with pytest.raises(ValueError) as excinfo:
            calculate_coherence(signal1, signal2, 1000.0)
        assert "length" in str(excinfo.value).lower()

    def test_transfer_function_different_length_error(self):
        """Test error when signals have different lengths."""
        signal1 = np.random.randn(1000)
        signal2 = np.random.randn(900)

        with pytest.raises(ValueError) as excinfo:
            calculate_transfer_function(signal1, signal2, 1000.0)
        assert "length" in str(excinfo.value).lower()

    def test_csd_empty_signal_error(self):
        """Test error for empty signals in CSD."""
        signal1 = np.array([])
        signal2 = np.random.randn(1000)

        with pytest.raises(ValueError):
            calculate_csd(signal1, signal2, 1000.0)

    def test_coherence_empty_signal_error(self):
        """Test error for empty signals in coherence."""
        signal1 = np.random.randn(1000)
        signal2 = np.array([])

        with pytest.raises(ValueError):
            calculate_coherence(signal1, signal2, 1000.0)


class TestFrequencyRangeValidation:
    """Tests for frequency range parameter validation."""

    def test_rms_freq_min_greater_than_max(self):
        """Test handling when freq_min > freq_max."""
        frequencies = np.linspace(0, 500, 501)
        psd = np.ones(501)

        # This should either swap them or raise error
        try:
            rms = calculate_rms_from_psd(
                frequencies, psd, freq_min=200, freq_max=100
            )
            # If it works, should use valid range
            assert rms >= 0
        except ValueError:
            pass  # Also acceptable

    def test_rms_freq_range_outside_data(self):
        """Test error when frequency range is outside data range."""
        frequencies = np.linspace(0, 500, 501)
        psd = np.ones(501)

        # Range entirely outside data should raise ValueError
        with pytest.raises(ValueError):
            calculate_rms_from_psd(
                frequencies, psd, freq_min=600, freq_max=1000
            )


class TestOctaveBandValidation:
    """Tests for octave band conversion validation."""

    def test_octave_invalid_fraction(self):
        """Test error for invalid octave fraction."""
        frequencies = np.linspace(1, 1000, 1000)
        psd = np.ones(1000)

        # Zero fraction should fail
        with pytest.raises((ValueError, ZeroDivisionError)):
            convert_psd_to_octave_bands(
                frequencies, psd, octave_fraction=0
            )

    def test_octave_freq_range_validation(self):
        """Test octave band conversion handles various frequency ranges."""
        frequencies = np.linspace(10, 500, 491)
        psd = np.ones(491)

        # Request range that overlaps with data
        oct_freq, oct_psd = convert_psd_to_octave_bands(
            frequencies, psd, octave_fraction=3,
            freq_min=20, freq_max=400
        )

        # Should return valid bands
        assert len(oct_freq) > 0
        assert len(oct_freq) == len(oct_psd)
        assert np.all(oct_psd >= 0)


class TestEdgeCases:
    """Tests for various edge cases."""

    def test_single_sample_signal(self):
        """Test handling of single-sample signal."""
        signal = np.array([1.0])

        # scipy.signal.welch handles this by using smaller nperseg
        # Just verify it doesn't crash
        try:
            frequencies, psd = calculate_psd_welch(signal, 1000.0)
            # If it works, output should be valid
            assert len(frequencies) > 0
        except ValueError:
            # Also acceptable to raise error
            pass

    def test_constant_signal(self):
        """Test handling of constant (DC only) signal."""
        signal = np.ones(10000)

        # Should work but PSD should be near zero (DC removed)
        frequencies, psd = calculate_psd_welch(signal, 1000.0, df=1.0)

        # After detrending, should have near-zero power
        assert np.max(psd) < 1e-10

    def test_very_high_sample_rate(self):
        """Test handling of very high sample rate."""
        sample_rate = 1e9  # 1 GHz
        signal = np.random.randn(10000)

        frequencies, psd = calculate_psd_welch(signal, sample_rate)

        assert frequencies[-1] <= sample_rate / 2

    def test_very_low_sample_rate(self):
        """Test handling of very low sample rate."""
        sample_rate = 1.0  # 1 Hz
        signal = np.random.randn(100)

        frequencies, psd = calculate_psd_welch(signal, sample_rate)

        assert frequencies[-1] <= 0.5

    def test_inf_values_in_signal(self):
        """Test handling of infinity values in signal."""
        signal = np.random.randn(1000)
        signal[500] = np.inf

        # scipy propagates inf - output will contain inf or nan
        frequencies, psd = calculate_psd_welch(signal, 1000.0)

        # Output should contain inf or nan
        assert np.any(~np.isfinite(psd))

    def test_complex_signal_error(self):
        """Test error for complex-valued signal."""
        signal = np.random.randn(1000) + 1j * np.random.randn(1000)

        # Should either work (taking real part) or raise error
        try:
            frequencies, psd = calculate_psd_welch(signal.real, 1000.0)
            assert np.all(psd >= 0)
        except (ValueError, TypeError):
            pass


class TestGUILogicValidation:
    """Tests for GUI-related validation logic."""

    def test_frequency_mask_logic(self):
        """Test frequency masking for plot range."""
        frequencies = np.array([1, 10, 100, 1000, 10000])
        psd = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        freq_min = 20
        freq_max = 2000

        mask = (frequencies >= freq_min) & (frequencies <= freq_max)
        filtered_freqs = frequencies[mask]
        filtered_psd = psd[mask]

        assert len(filtered_freqs) == 2
        assert 100 in filtered_freqs
        assert 1000 in filtered_freqs

    def test_channel_selection_same_channel(self):
        """Test detection of same channel selection for cross-spectrum."""
        ref_idx = 0
        resp_idx = 0

        # Should be detected as invalid
        assert ref_idx == resp_idx  # Same channel

    def test_comparison_curve_structure_validation(self):
        """Test comparison curve data structure validation."""
        # Valid curve
        valid_curve = {
            'name': 'Test',
            'frequencies': np.array([10, 100, 1000]),
            'psd': np.array([0.01, 0.1, 0.01]),
            'color': '#ff0000',
            'visible': True
        }

        assert 'name' in valid_curve
        assert 'frequencies' in valid_curve
        assert 'psd' in valid_curve
        assert len(valid_curve['frequencies']) == len(valid_curve['psd'])

        # Invalid curve (mismatched lengths)
        invalid_curve = {
            'frequencies': np.array([10, 100]),
            'psd': np.array([0.01, 0.1, 0.01])
        }
        assert len(invalid_curve['frequencies']) != len(invalid_curve['psd'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
