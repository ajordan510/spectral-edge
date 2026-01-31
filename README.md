# SpectralEdge: Advanced Signal Processing Suite

**SpectralEdge** is a professional-grade, cross-platform signal processing suite designed for engineers and scientists. It provides a graphical user interface (GUI) for interactive analysis, batch processing capabilities for large datasets, and a comprehensive library of signal processing functions. The suite is optimized for high-performance analysis of large datasets, with a focus on aerospace and mechanical vibration applications.

## Core Analytical Capabilities

SpectralEdge provides a robust set of tools for frequency-domain analysis, enabling deep insights into the spectral characteristics of dynamic signals. The core analytical capabilities are built on a foundation of industry-standard algorithms and best practices, ensuring accuracy and reliability.

### Power Spectral Density (PSD)

The Power Spectral Density (PSD) is a fundamental tool for characterizing the frequency content of a signal. It describes how the power of a signal is distributed over a range of frequencies, providing a statistical measure of the signal's energy content.

#### Analytical Approach

SpectralEdge implements two methods for PSD calculation:

1.  **Welch's Method (Averaged PSD):** This is the standard method for estimating the PSD of a signal. It involves dividing the signal into overlapping segments, applying a window function to each segment, computing the periodogram of each segment, and then averaging the periodograms. This process reduces the variance of the PSD estimate, providing a smoother and more statistically reliable result.

2.  **Maximax Envelope PSD:** This method is specifically designed for analyzing transient or non-stationary signals, and is widely used in aerospace applications for analyzing flight test data. It involves enveloping the spectra of a series of short, overlapping time segments to produce a "maxi-max" flight spectrum. This approach is particularly effective at capturing the worst-case spectral environment experienced by a system during a dynamic event.

#### Engineering Significance

The PSD is a critical tool for a wide range of engineering applications, including:

-   **Vibration Analysis:** Identifying dominant vibration frequencies and their corresponding energy levels.
-   **Structural Dynamics:** Characterizing the dynamic response of structures to external loads.
-   **Acoustic Analysis:** Analyzing the frequency content of sound and noise signals.
-   **Fatigue Analysis:** Estimating the fatigue life of components subjected to random vibration.

### Cross-Spectral Analysis

Cross-spectral analysis provides a powerful set of tools for understanding the relationships between two or more signals. It allows engineers to identify common frequency components, determine the phase relationship between signals, and characterize the transfer of energy between different parts of a system.

#### Analytical Approach

SpectralEdge provides a comprehensive suite of cross-spectral analysis tools, including:

-   **Cross-Spectral Density (CSD):** The CSD measures the correlation between two signals in the frequency domain. It is a complex quantity that contains both magnitude and phase information.
-   **Coherence:** The coherence function measures the linear relationship between two signals as a function of frequency. It provides a value between 0 and 1, where 1 indicates a perfect linear relationship and 0 indicates no linear relationship.
-   **Transfer Function (H1 Estimator):** The transfer function describes the input-output relationship of a linear system. It is calculated as the ratio of the cross-spectrum of the input and output signals to the power spectrum of the input signal.

#### Engineering Significance

Cross-spectral analysis is essential for a wide range of engineering applications, including:

-   **Source Identification:** Identifying the sources of noise and vibration in a system.
-   **Modal Analysis:** Determining the natural frequencies, damping ratios, and mode shapes of a structure.
-   **System Identification:** Characterizing the dynamic behavior of a system and developing mathematical models.
-   **Path Analysis:** Understanding the transmission paths of noise and vibration through a structure.

### Report Generation

SpectralEdge includes a powerful report generation feature that allows users to automatically create professional-quality reports in PowerPoint format. This feature is designed to streamline the process of documenting and communicating analysis results.

#### Features

-   **Customizable Templates:** Users can create their own PowerPoint templates to ensure that reports adhere to company branding and formatting guidelines.
-   **Embedded Plots:** PSD plots, spectrograms, and other visualizations can be embedded directly into the report.
-   **Summary Tables:** Analysis parameters, RMS values, and other key results can be presented in clear and concise tables.
-   **Automated Workflow:** The report generation process is fully automated, allowing users to create comprehensive reports with just a few clicks.

## Setup and Installation

### Windows

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ajordan510/spectral-edge.git
    cd spectral-edge
    ```

2.  **Run the application:**
    ```bash
    run.bat
    ```

### Linux

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ajordan510/spectral-edge.git
    cd spectral-edge
    ```

2.  **Create virtual environment and install dependencies:**
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python -m spectral_edge.main
    ```
