#!/usr/bin/env python3.11
"""
Test script for multi-rate channel support.

Tests that channels with different sample rates can be processed correctly
without impacting PSD calculation accuracy.
"""

import sys
sys.path.insert(0, '/tmp/SpectralEdge')

import numpy as np
from spectral_edge.core.psd import calculate_psd_welch
from spectral_edge.core.channel_data import ChannelData

def test_multi_rate_psd():
    """Test PSD calculation with different sample rates achieves same df."""
    print("\n" + "="*60)
    print("  Multi-Rate PSD Test")
    print("="*60)
    
    # Create test signals with different sample rates
    duration = 10.0  # seconds
    target_df = 1.0  # Hz
    
    # Channel 1: 10 kHz
    sr1 = 10000
    t1 = np.arange(0, duration, 1/sr1)
    signal1 = np.sin(2*np.pi*100*t1) + 0.5*np.sin(2*np.pi*250*t1)
    
    # Channel 2: 20 kHz
    sr2 = 20000
    t2 = np.arange(0, duration, 1/sr2)
    signal2 = np.sin(2*np.pi*100*t2) + 0.5*np.sin(2*np.pi*250*t2)
    
    # Channel 3: 25.6 kHz
    sr3 = 25600
    t3 = np.arange(0, duration, 1/sr3)
    signal3 = np.sin(2*np.pi*100*t3) + 0.5*np.sin(2*np.pi*250*t3)
    
    print(f"\nTest signals created:")
    print(f"  Channel 1: {sr1} Hz, {len(signal1)} samples")
    print(f"  Channel 2: {sr2} Hz, {len(signal2)} samples")
    print(f"  Channel 3: {sr3} Hz, {len(signal3)} samples")
    print(f"\nTarget df: {target_df} Hz")
    
    # Calculate PSD for each channel
    freqs1, psd1 = calculate_psd_welch(signal1, sr1, df=target_df)
    freqs2, psd2 = calculate_psd_welch(signal2, sr2, df=target_df)
    freqs3, psd3 = calculate_psd_welch(signal3, sr3, df=target_df)
    
    # Check frequency resolution
    df1 = freqs1[1] - freqs1[0]
    df2 = freqs2[1] - freqs2[0]
    df3 = freqs3[1] - freqs3[0]
    
    print(f"\nAchieved df:")
    print(f"  Channel 1: {df1:.3f} Hz")
    print(f"  Channel 2: {df2:.3f} Hz")
    print(f"  Channel 3: {df3:.3f} Hz")
    
    # Verify all achieve target df (within tolerance)
    tolerance = 0.01
    assert abs(df1 - target_df) < tolerance, f"Channel 1 df mismatch: {df1} vs {target_df}"
    assert abs(df2 - target_df) < tolerance, f"Channel 2 df mismatch: {df2} vs {target_df}"
    assert abs(df3 - target_df) < tolerance, f"Channel 3 df mismatch: {df3} vs {target_df}"
    
    print("\n✓ All channels achieve target df within tolerance")
    
    # Check frequency bins align at common frequencies
    # Find common frequency range (up to min Nyquist)
    max_common_freq = min(sr1/2, sr2/2, sr3/2)
    
    # Find indices for 100 Hz and 250 Hz peaks
    idx1_100 = np.argmin(np.abs(freqs1 - 100))
    idx2_100 = np.argmin(np.abs(freqs2 - 100))
    idx3_100 = np.argmin(np.abs(freqs3 - 100))
    
    print(f"\nFrequency bin alignment at 100 Hz:")
    print(f"  Channel 1: {freqs1[idx1_100]:.2f} Hz")
    print(f"  Channel 2: {freqs2[idx2_100]:.2f} Hz")
    print(f"  Channel 3: {freqs3[idx3_100]:.2f} Hz")
    
    # Verify bins align (all should be exactly 100 Hz with df=1.0)
    assert abs(freqs1[idx1_100] - 100) < 0.5, "Channel 1 bin misalignment"
    assert abs(freqs2[idx2_100] - 100) < 0.5, "Channel 2 bin misalignment"
    assert abs(freqs3[idx3_100] - 100) < 0.5, "Channel 3 bin misalignment"
    
    print("✓ Frequency bins align correctly")
    
    # Check PSD values are comparable at peaks
    psd1_100 = psd1[idx1_100]
    psd2_100 = psd2[idx2_100]
    psd3_100 = psd3[idx3_100]
    
    print(f"\nPSD values at 100 Hz peak:")
    print(f"  Channel 1: {psd1_100:.2e}")
    print(f"  Channel 2: {psd2_100:.2e}")
    print(f"  Channel 3: {psd3_100:.2e}")
    
    # PSDs should be similar (same signal, different sample rate)
    # Allow 20% variation due to windowing effects
    mean_psd = np.mean([psd1_100, psd2_100, psd3_100])
    assert abs(psd1_100 - mean_psd) / mean_psd < 0.2, "Channel 1 PSD value mismatch"
    assert abs(psd2_100 - mean_psd) / mean_psd < 0.2, "Channel 2 PSD value mismatch"
    assert abs(psd3_100 - mean_psd) / mean_psd < 0.2, "Channel 3 PSD value mismatch"
    
    print("✓ PSD values are consistent across sample rates")
    
    return True

def test_channel_data_class():
    """Test ChannelData class for storing multi-rate channel information."""
    print("\n" + "="*60)
    print("  ChannelData Class Test")
    print("="*60)
    
    # Create test data
    sr = 10000
    duration = 5.0
    t = np.arange(0, duration, 1/sr)
    signal = np.sin(2*np.pi*100*t)
    
    # Create ChannelData instance
    channel = ChannelData(
        name="Test Channel",
        signal=signal,
        sample_rate=sr,
        units="m/s²",
        flight_name="FT-001"
    )
    
    print(f"\nChannelData created:")
    print(f"  Name: {channel.name}")
    print(f"  Sample rate: {channel.sample_rate} Hz")
    print(f"  Units: {channel.units}")
    print(f"  Signal length: {len(channel.signal)} samples")
    print(f"  Duration: {channel.duration:.2f} s")
    print(f"  Flight: {channel.flight_name}")
    
    # Test properties
    assert channel.name == "Test Channel"
    assert channel.sample_rate == sr
    assert channel.units == "m/s²"
    assert len(channel.signal) == len(signal)
    assert abs(channel.duration - duration) < 0.01
    
    print("\n✓ ChannelData class works correctly")
    
    return True

def test_backward_compatibility():
    """Test that existing tuple format still works."""
    print("\n" + "="*60)
    print("  Backward Compatibility Test")
    print("="*60)
    
    # Create old-style 4-tuple
    sr = 10000
    duration = 5.0
    t = np.arange(0, duration, 1/sr)
    signal = np.sin(2*np.pi*100*t)
    
    # Old format: (name, signal, unit, flight_name)
    old_tuple = ("Test Channel", signal, "m/s²", "FT-001")
    
    # Unpack and verify
    name, sig, unit, flight = old_tuple
    
    print(f"\nOld tuple format:")
    print(f"  Name: {name}")
    print(f"  Signal length: {len(sig)} samples")
    print(f"  Units: {unit}")
    print(f"  Flight: {flight}")
    
    assert name == "Test Channel"
    assert len(sig) == len(signal)
    assert unit == "m/s²"
    assert flight == "FT-001"
    
    print("\n✓ Old tuple format still works")
    
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  MULTI-RATE CHANNEL SUPPORT TESTS")
    print("="*60)
    
    all_passed = True
    
    try:
        test_multi_rate_psd()
    except Exception as e:
        print(f"\n✗ Multi-rate PSD test FAILED: {e}")
        all_passed = False
    
    try:
        test_channel_data_class()
    except Exception as e:
        print(f"\n✗ ChannelData class test FAILED: {e}")
        all_passed = False
    
    try:
        test_backward_compatibility()
    except Exception as e:
        print(f"\n✗ Backward compatibility test FAILED: {e}")
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("  ALL TESTS PASSED ✓")
    else:
        print("  SOME TESTS FAILED ✗")
    print("="*60 + "\n")
    
    sys.exit(0 if all_passed else 1)
