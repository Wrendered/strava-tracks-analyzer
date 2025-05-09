"""
Unified wind direction estimation API.

This module provides a single consistent API for wind direction estimation
with different algorithms and confidence levels.
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Union, Literal

from core.wind.models import WindEstimate
from core.wind.direction import (
    estimate_wind_direction_from_upwind_tacks,
    iterative_wind_estimation,
    estimate_balanced_wind_direction
)
from core.segments import analyze_wind_angles

logger = logging.getLogger(__name__)

# Type definitions
EstimationMethod = Literal["simple", "balanced", "iterative", "auto"]

def estimate_wind_direction(
    stretches: pd.DataFrame,
    initial_wind_direction: float,
    method: EstimationMethod = "auto",
    suspicious_angle_threshold: float = 20,
    confidence_threshold: Optional[float] = None,
) -> WindEstimate:
    """
    Unified API for wind direction estimation with confidence levels.
    
    This function provides a single interface for all wind estimation methods,
    selecting the appropriate algorithm based on the available data and method preference.
    
    Args:
        stretches: DataFrame with sailing segments
        initial_wind_direction: Initial user-provided wind direction
        method: Estimation method to use:
            - "simple": Simple estimation using upwind tacks (fastest, good for quick estimates)
            - "balanced": Balanced estimation that equalizes port and starboard tacks
            - "iterative": Most sophisticated algorithm with outlier filtering (most accurate)
            - "auto": Automatically select the best method based on data
        suspicious_angle_threshold: Angles < this are considered suspicious (default 20°)
        confidence_threshold: Optional minimum confidence threshold for result acceptance
            
    Returns:
        WindEstimate: Wind direction estimation result with confidence level
    """
    if stretches is None or stretches.empty:
        # Return user input with no confidence
        return WindEstimate.from_user_input(initial_wind_direction)
    
    # Determine estimation method based on data quality and user preference
    if method == "auto":
        # Automatically select method based on data quality
        # For now, default to iterative which is the most robust
        method = "iterative"
    
    # Make sure we have wind angles calculated
    if 'angle_to_wind' not in stretches.columns or 'tack' not in stretches.columns:
        try:
            # Use initial wind direction to calculate angles before estimation
            analyzed_stretches = analyze_wind_angles(stretches.copy(), initial_wind_direction)
        except Exception as e:
            logger.error(f"Error analyzing wind angles: {e}")
            # Default to user input with no confidence
            return WindEstimate.from_user_input(initial_wind_direction)
    else:
        analyzed_stretches = stretches.copy()
    
    # Calculate confidence level based on data quality
    from core.wind.models import determine_confidence_level
    confidence = determine_confidence_level(analyzed_stretches)
    
    # If confidence is 'none' and not explicitly requested, return user input
    if confidence == "none" and method != "simple" and method != "balanced":
        return WindEstimate.from_user_input(initial_wind_direction)
    
    # Extract port and starboard data for the result
    port_tack = analyzed_stretches[analyzed_stretches['tack'] == 'Port']
    starboard_tack = analyzed_stretches[analyzed_stretches['tack'] == 'Starboard']
    
    port_upwind = port_tack[port_tack['angle_to_wind'] < 90]
    starboard_upwind = starboard_tack[starboard_tack['angle_to_wind'] < 90]
    
    # Get best angles for each tack
    port_angle = port_upwind['angle_to_wind'].min() if not port_upwind.empty else None
    starboard_angle = starboard_upwind['angle_to_wind'].min() if not starboard_upwind.empty else None
    
    # Perform wind direction estimation using the selected method
    estimated_wind = None
    
    try:
        if method == "simple":
            estimated_wind = estimate_wind_direction_from_upwind_tacks(
                analyzed_stretches, 
                suspicious_angle_threshold
            )
            logger.info(f"Simple wind estimation result: {estimated_wind:.1f}°")
            
        elif method == "balanced":
            estimated_wind = estimate_balanced_wind_direction(
                analyzed_stretches,
                initial_wind_direction,
                suspicious_angle_threshold,
                filter_suspicious=True
            )
            logger.info(f"Balanced wind estimation result: {estimated_wind:.1f}°")
            
        elif method == "iterative":
            estimated_wind = iterative_wind_estimation(
                analyzed_stretches,
                initial_wind_direction,
                suspicious_angle_threshold,
                max_iterations=3
            )
            logger.info(f"Iterative wind estimation result: {estimated_wind:.1f}°")
            
    except Exception as e:
        logger.error(f"Error in wind estimation: {e}")
        # Use user input if estimation fails
        estimated_wind = initial_wind_direction
    
    # Fallback to user input if estimation failed
    if estimated_wind is None:
        logger.warning("Wind estimation failed, using user input")
        return WindEstimate.from_user_input(initial_wind_direction)
    
    # Create the WindEstimate result
    result = WindEstimate(
        direction=estimated_wind,
        confidence=confidence,
        port_angle=port_angle,
        starboard_angle=starboard_angle,
        port_count=len(port_upwind),
        starboard_count=len(starboard_upwind),
        user_provided=False
    )
    
    logger.info(f"Wind direction estimate: {result.direction:.1f}° with {result.confidence} confidence")
    
    return result