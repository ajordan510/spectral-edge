"""
Generate sample vibration data for testing SpectralEdge.

This script creates a synthetic vibration signal with multiple frequency
components and saves it as a CSV file in the data directory.

Run this script from the project root directory:
    python scripts/generate_sample_data.py

Author: SpectralEdge Development Team
"""

import numpy as np
import pandas as pd
from pathlib import Path


def generate_sample_vibration_data():
    """
    Generate sample vibration data with multiple frequency components.
    
    Creates a realistic vibration signal containing:
    - 10 Hz low frequency component
    - 60 Hz power line frequency
    - 120 Hz harmonic
    - 500 Hz high frequency component
    - Random noise
    
    The data is saved to data/sample_vibration_data.csv
    """
    print("Generating sample vibration data...")
    
    # Signal parameters
    sample_rate = 5000.0  # 5000 Hz (high rate sampling)
    duration = 10.0  # 10 seconds
    num_samples = int(sample_rate * duration)
    
    # Create time array
    time = np.linspace(0, duration, num_samples)
    
    # Create signal with multiple frequency components
    # These simulate different vibration sources in a mechanical system
    
    # 10 Hz component (low frequency vibration, e.g., from rotating machinery)
    signal_10hz = 0.5 * np.sin(2 * np.pi * 10 * time)
    
    # 60 Hz component (power line frequency interference)
    signal_60hz = 0.3 * np.sin(2 * np.pi * 60 * time)
    
    # 120 Hz component (harmonic of 60 Hz)
    signal_120hz = 0.2 * np.sin(2 * np.pi * 120 * time)
    
    # 500 Hz component (high frequency vibration)
    signal_500hz = 0.15 * np.sin(2 * np.pi * 500 * time)
    
    # Add some random noise to make it realistic
    noise = 0.05 * np.random.randn(num_samples)
    
    # Combine all components for Channel 1 (Accelerometer X-axis)
    channel1 = signal_10hz + signal_60hz + signal_120hz + signal_500hz + noise
    
    # Channel 2 (Accelerometer Y-axis) has different amplitudes
    channel2 = 0.8 * signal_10hz + 0.5 * signal_60hz + noise * 0.8
    
    # Create DataFrame
    df = pd.DataFrame({
        'Time': time,
        'Accelerometer_X': channel1,
        'Accelerometer_Y': channel2
    })
    
    # Ensure data directory exists
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # Save to CSV
    output_file = data_dir / 'sample_vibration_data.csv'
    df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"\n✓ Sample data created successfully!")
    print(f"  File: {output_file}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {duration} seconds")
    print(f"  Total samples: {num_samples}")
    print(f"  Channels: 2 (Accelerometer_X, Accelerometer_Y)")
    print(f"  Frequency components: 10, 60, 120, 500 Hz")
    print(f"\nYou can now load this file in the PSD Analysis tool!")


if __name__ == "__main__":
    generate_sample_vibration_data()
