"""
Legacy calculations module - now re-exports from core.calculations.

This module maintains backward compatibility while delegating to the 
consolidated calculations in core.calculations.
"""

# Re-export all functions from the consolidated module
from core.calculations import (
    calculate_bearing,
    calculate_distance,
    angle_to_wind,
    calculate_angle_bisector,
    meters_per_second_to_knots,
    knots_to_meters_per_second,
    meters_to_kilometers,
    kilometers_to_meters,
    analyze_wind_angles,
    determine_tack,
    calculate_vmg,
    calculate_vmg_upwind,
    calculate_vmg_downwind,
    calculate_track_metrics,
    calculate_segment_quality_score,
    calculate_average_angle_from_segments
)

# Maintain backward compatibility
__all__ = [
    'calculate_bearing',
    'calculate_distance', 
    'angle_to_wind',
    'calculate_angle_bisector',
    'meters_per_second_to_knots',
    'knots_to_meters_per_second',
    'calculate_track_metrics',
    'calculate_average_angle_from_segments',
    'analyze_wind_angles'
]