"""
Helper functions for wind direction estimation.

This module contains focused helper functions to break down the complex
wind estimation algorithm into manageable, testable pieces.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

from core.wind.models import WindEstimate
from core.constants import (
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD, UPWIND_DOWNWIND_BOUNDARY_DEGREES,
    MIN_SEGMENTS_FOR_ESTIMATION, DEFAULT_MIN_SEGMENT_DISTANCE_METERS,
    MIN_RELIABLE_SEGMENT_LENGTH_METERS, HIGH_CONFIDENCE_MIN_DISTANCE_METERS,
    MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES, MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES,
    FULL_CIRCLE_DEGREES
)

logger = logging.getLogger(__name__)


def filter_and_validate_segments(
    segments: pd.DataFrame,
    user_wind_direction: float,
    suspicious_angle_threshold: float,
    min_segment_distance: float
) -> Tuple[pd.DataFrame, WindEstimate]:
    """
    Filter and validate segments for wind estimation.
    
    Returns:
        Tuple of (filtered_segments, fallback_result_if_insufficient_data)
    """
    # Initialize fallback result
    fallback_result = WindEstimate(
        direction=user_wind_direction,
        confidence="None",
        user_provided=True,
        port_angle=None,
        starboard_angle=None,
        port_segments=0,
        starboard_segments=0,
        total_segments=len(segments) if not segments.empty else 0
    )
    
    # Basic validation
    if segments.empty:
        logger.warning("No segments provided for wind estimation")
        return segments, fallback_result
    
    # Validate required columns
    required_columns = ['angle_to_wind', 'tack', 'distance']
    missing_columns = [col for col in required_columns if col not in segments.columns]
    if missing_columns:
        logger.warning(f"Missing required columns: {missing_columns}")
        return segments, fallback_result
    
    # Filter by distance
    filtered = segments[segments['distance'] >= min_segment_distance].copy()
    logger.info(f"After distance filtering (≥{min_segment_distance}m): {len(filtered)}/{len(segments)} segments")
    
    if len(filtered) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning(f"Insufficient segments after filtering: {len(filtered)} < {MIN_SEGMENTS_FOR_ESTIMATION}")
        return filtered, fallback_result
    
    # Filter upwind segments
    upwind = filtered[filtered['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES].copy()
    logger.info(f"Upwind segments: {len(upwind)}/{len(filtered)}")
    
    if len(upwind) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning(f"Insufficient upwind segments: {len(upwind)} < {MIN_SEGMENTS_FOR_ESTIMATION}")
        return upwind, fallback_result
    
    # Filter suspicious angles
    clean_upwind = upwind[upwind['angle_to_wind'] >= suspicious_angle_threshold].copy()
    suspicious_count = len(upwind) - len(clean_upwind)
    
    if suspicious_count > 0:
        logger.info(f"Filtered {suspicious_count} suspicious angles < {suspicious_angle_threshold}°")
    
    if len(clean_upwind) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning(f"Insufficient clean upwind segments: {len(clean_upwind)} < {MIN_SEGMENTS_FOR_ESTIMATION}")
        return clean_upwind, fallback_result
    
    return clean_upwind, None


def calculate_weighted_tack_averages(segments: pd.DataFrame) -> Tuple[Optional[float], Optional[float], int, int]:
    """
    Calculate distance-weighted average angles for port and starboard tacks.
    
    Returns:
        Tuple of (port_avg_angle, starboard_avg_angle, port_count, starboard_count)
    """
    port_tack = segments[segments['tack'] == 'Port']
    starboard_tack = segments[segments['tack'] == 'Starboard']
    
    port_avg_angle = None
    starboard_avg_angle = None
    
    if len(port_tack) > 0:
        port_weights = port_tack['distance'].values
        port_angles = port_tack['angle_to_wind'].values
        port_avg_angle = np.average(port_angles, weights=port_weights)
        logger.debug(f"Port tack: {len(port_tack)} segments, weighted avg angle: {port_avg_angle:.1f}°")
    
    if len(starboard_tack) > 0:
        starboard_weights = starboard_tack['distance'].values
        starboard_angles = starboard_tack['angle_to_wind'].values
        starboard_avg_angle = np.average(starboard_angles, weights=starboard_weights)
        logger.debug(f"Starboard tack: {len(starboard_tack)} segments, weighted avg angle: {starboard_avg_angle:.1f}°")
    
    return port_avg_angle, starboard_avg_angle, len(port_tack), len(starboard_tack)


def estimate_wind_from_tacks(
    user_wind_direction: float,
    port_avg_angle: Optional[float],
    starboard_avg_angle: Optional[float]
) -> float:
    """
    Estimate wind direction from port and starboard tack angles.
    
    Returns:
        Estimated wind direction in degrees
    """
    if port_avg_angle is not None and starboard_avg_angle is not None:
        # Calculate the difference and adjust wind direction
        angle_difference = starboard_avg_angle - port_avg_angle
        wind_adjustment = angle_difference / 2.0
        estimated_wind = (user_wind_direction - wind_adjustment) % FULL_CIRCLE_DEGREES
        
        logger.info(f"Tack angle difference: {angle_difference:.1f}°")
        logger.info(f"Wind adjustment: {wind_adjustment:.1f}°")
        logger.info(f"Estimated wind: {user_wind_direction:.1f}° → {estimated_wind:.1f}°")
        
        return estimated_wind
    
    elif port_avg_angle is not None:
        # Only port tack available
        logger.info("Only port tack available for wind estimation")
        return user_wind_direction
    
    elif starboard_avg_angle is not None:
        # Only starboard tack available
        logger.info("Only starboard tack available for wind estimation")
        return user_wind_direction
    
    else:
        # No valid tacks
        logger.warning("No valid tacks for wind estimation")
        return user_wind_direction


def determine_confidence_level(
    segments: pd.DataFrame,
    port_count: int,
    starboard_count: int,
    port_avg_angle: Optional[float],
    starboard_avg_angle: Optional[float]
) -> str:
    """
    Determine confidence level based on data quality and balance.
    
    Returns:
        Confidence level string: "High", "Medium", "Low", or "None"
    """
    total_distance = segments['distance'].sum()
    total_segments = len(segments)
    
    # Check basic requirements
    if total_segments < MIN_SEGMENTS_FOR_ESTIMATION:
        return "None"
    
    if port_count == 0 or starboard_count == 0:
        return "Low"
    
    if port_avg_angle is None or starboard_avg_angle is None:
        return "Low"
    
    # High confidence criteria
    if (total_distance >= HIGH_CONFIDENCE_MIN_DISTANCE_METERS and
        total_segments >= 10 and
        min(port_count, starboard_count) >= 3 and
        abs(port_avg_angle - starboard_avg_angle) <= MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES):
        return "High"
    
    # Medium confidence criteria
    if (total_segments >= 6 and
        min(port_count, starboard_count) >= 2 and
        abs(port_avg_angle - starboard_avg_angle) <= MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES):
        return "Medium"
    
    # Otherwise low confidence
    return "Low"