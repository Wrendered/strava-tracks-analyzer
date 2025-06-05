"""
Wind estimation module.

This module provides all wind direction estimation functionality with clean,
organized interfaces. All algorithms have been consolidated for maintainability.
"""

# Import the main algorithms
from .algorithms import (
    estimate_wind_direction_iterative,
    estimate_wind_direction_weighted,
    user_guided_wind_estimation,
    bearing_cluster_analysis,
    calculate_wind_score,
    calculate_angle_bisector
)

# Import models
from .models import WindEstimate

# Import utilities (if any other files need them)
try:
    from .direction import estimate_wind_direction_from_upwind_tacks
except ImportError:
    pass

__all__ = [
    'estimate_wind_direction_iterative',
    'estimate_wind_direction_weighted', 
    'user_guided_wind_estimation',
    'bearing_cluster_analysis',
    'calculate_wind_score',
    'calculate_angle_bisector',
    'WindEstimate',
    'estimate_wind_direction_from_upwind_tacks'
]