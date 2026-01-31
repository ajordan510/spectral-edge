#!/bin/bash
# Run headless GUI tests for SpectralEdge
#
# Usage:
#   ./scripts/run_headless_tests.sh           # Run all tests
#   ./scripts/run_headless_tests.sh -k cross  # Run tests matching "cross"
#   ./scripts/run_headless_tests.sh -v        # Verbose output

set -e

# Check if xvfb-run is available (Linux with X11)
if command -v xvfb-run &> /dev/null; then
    echo "Running tests with Xvfb virtual framebuffer..."
    xvfb-run -a pytest tests/ "$@"
else
    # Use Qt's offscreen platform (works on any system)
    echo "Running tests with Qt offscreen platform..."
    QT_QPA_PLATFORM=offscreen pytest tests/ "$@"
fi
