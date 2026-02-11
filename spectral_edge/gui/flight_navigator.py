"""Legacy compatibility wrapper for the unified navigator.

This module is deprecated. Import from `spectral_edge.gui.flight_navigator_enhanced`
instead.
"""

from spectral_edge.gui.flight_navigator_enhanced import (
    FlightNavigator,
    EnhancedFlightNavigator,
)

__all__ = ["FlightNavigator", "EnhancedFlightNavigator"]
