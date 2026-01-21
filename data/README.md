# Sample Data

This directory contains sample data files for testing SpectralEdge tools.

## sample_vibration_data.csv

A synthetic vibration signal with the following characteristics:

- **Sample Rate**: 5000 Hz
- **Duration**: 10 seconds
- **Channels**: 2 (Accelerometer_X, Accelerometer_Y)
- **Frequency Components**:
  - 10 Hz (low frequency vibration)
  - 60 Hz (power line frequency)
  - 120 Hz (harmonic)
  - 500 Hz (high frequency component)
- **Noise**: Small amount of random noise added

This file can be used to test the PSD Analysis tool and verify that it correctly identifies the frequency components.

## Usage

1. Launch SpectralEdge
2. Click on "PSD Analysis"
3. Click "Load CSV File" and select `sample_vibration_data.csv`
4. Click "Calculate PSD"
5. You should see peaks at 10, 60, 120, and 500 Hz in the plot
