"""
Legacy analysis module - now re-exports from consolidated modules.

This module maintains backward compatibility while delegating to the 
properly organized modules in core.
"""

# Re-export segment detection from core.segments
from core.segments import find_consistent_angle_stretches

# Re-export wind analysis from core.calculations 
from core.calculations import analyze_wind_angles

# Re-export wind estimation from core.wind
from core.wind.algorithms import estimate_wind_direction_iterative

# Simple upwind tack estimation (kept here for now since it's used by wind algorithms)
from core.constants import (
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD, UPWIND_DOWNWIND_BOUNDARY_DEGREES,
    MIN_SEGMENTS_FOR_ESTIMATION, ANGLE_WRAP_BOUNDARY_DEGREES, FULL_CIRCLE_DEGREES
)
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def estimate_wind_direction_from_upwind_tacks(stretches, suspicious_angle_threshold=DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD):
    """
    SIMPLIFIED algorithm to estimate wind direction based on upwind tacks.
    
    This method:
    1. Selects upwind segments (angle_to_wind < UPWIND_DOWNWIND_BOUNDARY_DEGREES)
    2. Filters out suspicious angles (< suspicious_angle_threshold° to wind)
    3. Gets average angles for port and starboard tacks
    4. Calculates wind direction from the bisector of the best port and starboard tracks
    
    Parameters:
    - stretches: DataFrame with sailing segments
    - suspicious_angle_threshold: Angles less than this are excluded (default: 20°)
    
    Returns:
    - Estimated wind direction or None if insufficient data
    """
    logger.info("Starting upwind tack analysis for wind direction estimation")
    
    # Filter to upwind segments only and exclude suspicious angles
    upwind = stretches[
        (stretches['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES) &
        (stretches['angle_to_wind'] >= suspicious_angle_threshold)
    ]
    
    logger.info(f"Found {len(upwind)} " + 
                f"upwind segments after removing angles < {suspicious_angle_threshold}°")
    
    if len(upwind) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning("Not enough good upwind segments for wind estimation")
        return None
    
    # Separate port and starboard tacks
    port_tacks = upwind[upwind['tack'] == 'Port']
    starboard_tacks = upwind[upwind['tack'] == 'Starboard']
    
    if len(port_tacks) == 0 or len(starboard_tacks) == 0:
        logger.warning("Need both port and starboard tacks for wind estimation")
        return None
    
    # Get distance-weighted average bearings for each tack
    port_weights = port_tacks['distance'].values
    port_bearings = port_tacks['bearing'].values
    port_best_bearing = np.average(port_bearings, weights=port_weights)
    
    starboard_weights = starboard_tacks['distance'].values
    starboard_bearings = starboard_tacks['bearing'].values
    starboard_best_bearing = np.average(starboard_bearings, weights=starboard_weights)
    
    # Calculate average angles to wind for validation
    port_best_angle = np.average(port_tacks['angle_to_wind'].values, weights=port_weights)
    starboard_best_angle = np.average(starboard_tacks['angle_to_wind'].values, weights=starboard_weights)
    
    logger.info(f"Port tack: bearing {port_best_bearing:.1f}°, angle {port_best_angle:.1f}°")
    logger.info(f"Starboard tack: bearing {starboard_best_bearing:.1f}°, angle {starboard_best_angle:.1f}°")
    
    # Check if the tacks are reasonably opposite (they should be)
    bearing_diff = abs(port_best_bearing - starboard_best_bearing)
    if bearing_diff > ANGLE_WRAP_BOUNDARY_DEGREES:
        bearing_diff = FULL_CIRCLE_DEGREES - bearing_diff
    
    if bearing_diff < UPWIND_DOWNWIND_BOUNDARY_DEGREES:
        logger.warning(f"Port and starboard bearings too similar ({bearing_diff:.1f}° apart)")
        return None
    
    current_wind = stretches.get('wind_direction', [None])[0] if 'wind_direction' in stretches.columns else None
    
    # Calculate wind direction from port tack
    if port_best_bearing is not None and port_best_angle is not None:
        # Wind = port bearing - port angle to wind
        estimated_wind = (port_best_bearing - port_best_angle) % FULL_CIRCLE_DEGREES
        logger.info(f"Estimated wind from port tack: {estimated_wind:.1f}°")
        return estimated_wind
        
    elif starboard_best_bearing is not None:
        # Wind = starboard bearing - starboard angle to wind
        estimated_wind = (starboard_best_bearing - starboard_best_angle) % FULL_CIRCLE_DEGREES
        logger.info(f"Estimated wind from starboard tack: {estimated_wind:.1f}°")
        return estimated_wind
    
    # Fallback to user-provided wind
    return current_wind


def estimate_wind_direction(stretches, use_simple_method=True, user_wind_direction=None):
    """
    Estimate wind direction based on sailing patterns.
    
    This is the main entry point for wind estimation. The complex logic has been
    refactored into separate, focused functions for better maintainability.
    
    Parameters:
    - stretches: DataFrame of consistent sailing segments
    - use_simple_method: If True, uses the refined balanced tack algorithm (recommended)
    - user_wind_direction: Optional user-provided wind direction to use as a starting point
    
    Returns:
    - Estimated wind direction in degrees, or None if estimation fails
    """
    # Use the fixed iterative algorithm if we have a user wind direction
    if user_wind_direction is not None:
        result = estimate_wind_direction_iterative(
            stretches,
            user_wind_direction,
            max_iterations=5
        )
        return result.direction
    
    # Fallback for cases without user input
    logger.warning("No user wind direction provided for estimation")
    return None


# Maintain backward compatibility
__all__ = [
    'find_consistent_angle_stretches',
    'analyze_wind_angles',
    'estimate_wind_direction_from_upwind_tacks',
    'estimate_wind_direction'
]