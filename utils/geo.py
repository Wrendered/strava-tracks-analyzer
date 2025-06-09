"""
Legacy geographic utilities module - now re-exports from core.calculations.

This module maintains backward compatibility while delegating to the 
consolidated calculations in core.calculations.
"""

# Re-export all geographic functions from the consolidated module
from core.calculations import (
    calculate_bearing,
    calculate_distance,
    angle_to_wind,
    meters_per_second_to_knots,
    knots_to_meters_per_second
)

# Maintain backward compatibility
__all__ = [
    'calculate_bearing',
    'calculate_distance',
    'angle_to_wind',
    'meters_per_second_to_knots',
    'knots_to_meters_per_second'
]