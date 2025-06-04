"""
Fixed wind estimation algorithm with proper tack reclassification.

This module implements the corrected wind estimation that reclassifies segments
after each wind direction adjustment to ensure balanced port/starboard angles.
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional, Tuple

from core.constants import (
    FULL_CIRCLE_DEGREES, UPWIND_DOWNWIND_BOUNDARY_DEGREES,
    MIN_SEGMENTS_FOR_ESTIMATION, DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_MIN_SEGMENT_DISTANCE_METERS, MIN_RELIABLE_SEGMENT_LENGTH_METERS,
    HIGH_CONFIDENCE_MIN_DISTANCE_METERS, MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES,
    MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES, WIND_CONVERGENCE_THRESHOLD_DEGREES
)
from core.wind.models import WindEstimate
from core.metrics_advanced import (
    detect_suspicious_segments, calculate_segment_quality_score
)
from utils.analysis import analyze_wind_angles

logger = logging.getLogger(__name__)


def estimate_wind_direction_iterative(
    stretches: pd.DataFrame,
    initial_wind: float,
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE_METERS,
    max_iterations: int = 5
) -> WindEstimate:
    """
    Estimate wind direction with proper iterative tack reclassification.
    
    This is the FIXED algorithm that:
    1. Starts with an initial wind estimate
    2. Classifies segments as port/starboard based on current wind
    3. Calculates average angles for each tack
    4. Adjusts wind to balance the angles
    5. RECLASSIFIES segments with new wind estimate
    6. Repeats until convergence
    
    Args:
        stretches: DataFrame with sailing segments (must have bearing, distance columns)
        initial_wind: Initial wind direction estimate (degrees)
        suspicious_angle_threshold: Minimum angle to wind to consider valid
        min_segment_distance: Minimum segment distance to consider
        max_iterations: Maximum iterations before giving up
        
    Returns:
        WindEstimate with balanced port/starboard angles
    """
    # Initialize result
    result = WindEstimate(
        direction=initial_wind,
        confidence="low",
        user_provided=True,
        port_angle=None,
        starboard_angle=None,
        port_count=0,
        starboard_count=0
    )
    
    # Validate input
    if stretches is None or stretches.empty:
        logger.warning("No stretches provided for wind estimation")
        return result
    
    # Make a copy to avoid modifying original
    working_stretches = stretches.copy()
    
    # Track convergence
    current_wind = initial_wind
    previous_wind = None
    iteration_history = []
    
    logger.info(f"Starting iterative wind estimation with initial wind: {initial_wind:.1f}°")
    
    for iteration in range(max_iterations):
        logger.info(f"\n--- Iteration {iteration + 1} ---")
        
        # Step 1: Analyze segments with current wind estimate
        # This is the KEY FIX - we reclassify on each iteration!
        analyzed = analyze_wind_angles(working_stretches, current_wind)
        
        # Step 2: Filter to upwind segments only
        upwind = analyzed[analyzed['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES].copy()
        
        # Step 3: Filter out suspicious segments
        if len(upwind) > 0:
            suspicious_segments = detect_suspicious_segments(
                upwind,
                min_angle_to_wind=suspicious_angle_threshold,
                min_segment_length=MIN_RELIABLE_SEGMENT_LENGTH_METERS
            )
            upwind_filtered = suspicious_segments[~suspicious_segments['suspicious']]
            
            if len(suspicious_segments) > len(upwind_filtered):
                logger.info(f"Filtered out {len(suspicious_segments) - len(upwind_filtered)} suspicious segments")
            
            upwind = upwind_filtered
        
        # Step 4: Apply minimum distance filter
        if min_segment_distance > 0 and len(upwind) > 0:
            upwind = upwind[upwind['distance'] >= min_segment_distance]
            logger.info(f"Using {len(upwind)} upwind segments with distance >= {min_segment_distance}m")
        
        # Check if we have enough segments
        if len(upwind) < MIN_SEGMENTS_FOR_ESTIMATION:
            logger.warning(f"Insufficient upwind segments ({len(upwind)}) for estimation")
            if iteration == 0:
                return result  # Failed on first iteration
            else:
                break  # Use previous iteration's result
        
        # Step 5: Split by tack (using current wind's classification)
        port_tack = upwind[upwind['tack'] == 'Port']
        starboard_tack = upwind[upwind['tack'] == 'Starboard']
        
        logger.info(f"Tack distribution: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
        
        # Need at least one segment in each tack
        if len(port_tack) == 0 or len(starboard_tack) == 0:
            logger.warning("Missing one tack, cannot balance")
            if iteration == 0:
                return result
            else:
                break
        
        # Step 6: Calculate weighted average angles for each tack
        # Use median for robustness against outliers
        port_angles = port_tack['angle_to_wind'].values
        starboard_angles = starboard_tack['angle_to_wind'].values
        
        # Use median for robustness
        port_median = np.median(port_angles)
        starboard_median = np.median(starboard_angles)
        
        # Also calculate weighted averages for comparison
        port_weights = port_tack['distance'].values
        starboard_weights = starboard_tack['distance'].values
        
        port_weighted_avg = np.average(port_angles, weights=port_weights)
        starboard_weighted_avg = np.average(starboard_angles, weights=starboard_weights)
        
        logger.info(f"Port angles: median={port_median:.1f}°, weighted_avg={port_weighted_avg:.1f}°")
        logger.info(f"Starboard angles: median={starboard_median:.1f}°, weighted_avg={starboard_weighted_avg:.1f}°")
        
        # Step 7: Calculate wind adjustment to balance angles
        # Use median for more robust estimation
        angle_imbalance = starboard_median - port_median
        wind_adjustment = angle_imbalance / 2.0
        
        # Calculate new wind estimate
        new_wind = (current_wind - wind_adjustment) % FULL_CIRCLE_DEGREES
        
        logger.info(f"Angle imbalance: {angle_imbalance:.1f}°, Wind adjustment: {wind_adjustment:.1f}°")
        logger.info(f"New wind estimate: {new_wind:.1f}° (was {current_wind:.1f}°)")
        
        # Track iteration history
        iteration_history.append({
            'iteration': iteration + 1,
            'wind': new_wind,
            'port_median': port_median,
            'starboard_median': starboard_median,
            'imbalance': abs(angle_imbalance),
            'port_count': len(port_tack),
            'starboard_count': len(starboard_tack)
        })
        
        # Step 8: Check for convergence
        if abs(new_wind - current_wind) < WIND_CONVERGENCE_THRESHOLD_DEGREES:
            logger.info(f"✓ Converged! Wind direction stabilized at {new_wind:.1f}°")
            current_wind = new_wind
            break
        
        # Check if we're oscillating
        if previous_wind is not None and abs(new_wind - previous_wind) < WIND_CONVERGENCE_THRESHOLD_DEGREES:
            logger.info(f"✓ Detected oscillation, taking average of last two estimates")
            current_wind = (current_wind + new_wind) / 2.0
            break
        
        # Update for next iteration
        previous_wind = current_wind
        current_wind = new_wind
    
    # Final analysis with converged wind direction
    final_analyzed = analyze_wind_angles(working_stretches, current_wind)
    final_upwind = final_analyzed[final_analyzed['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES]
    
    # Apply same filtering as in iterations
    if len(final_upwind) > 0:
        suspicious_segments = detect_suspicious_segments(
            final_upwind,
            min_angle_to_wind=suspicious_angle_threshold,
            min_segment_length=MIN_RELIABLE_SEGMENT_LENGTH_METERS
        )
        final_upwind = suspicious_segments[~suspicious_segments['suspicious']]
    
    if min_segment_distance > 0 and len(final_upwind) > 0:
        final_upwind = final_upwind[final_upwind['distance'] >= min_segment_distance]
    
    # Get final statistics
    final_port = final_upwind[final_upwind['tack'] == 'Port']
    final_starboard = final_upwind[final_upwind['tack'] == 'Starboard']
    
    # Calculate final angles
    port_angle = None
    starboard_angle = None
    
    if len(final_port) > 0:
        port_angle = np.median(final_port['angle_to_wind'].values)
    
    if len(final_starboard) > 0:
        starboard_angle = np.median(final_starboard['angle_to_wind'].values)
    
    # Determine confidence level
    confidence = "low"
    if port_angle is not None and starboard_angle is not None:
        final_imbalance = abs(port_angle - starboard_angle)
        total_distance = final_upwind['distance'].sum()
        
        # High confidence if well-balanced and sufficient data
        if (final_imbalance < MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES and 
            len(final_port) >= MIN_SEGMENTS_FOR_ESTIMATION and 
            len(final_starboard) >= MIN_SEGMENTS_FOR_ESTIMATION and
            total_distance > HIGH_CONFIDENCE_MIN_DISTANCE_METERS):
            confidence = "high"
        elif final_imbalance < MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES:
            confidence = "medium"
    
    # Log final results
    logger.info(f"\n--- Final Results ---")
    logger.info(f"Converged wind direction: {current_wind:.1f}°")
    logger.info(f"Final port angle: {port_angle:.1f}° ({len(final_port)} segments)" if port_angle else "No port segments")
    logger.info(f"Final starboard angle: {starboard_angle:.1f}° ({len(final_starboard)} segments)" if starboard_angle else "No starboard segments")
    if port_angle and starboard_angle:
        logger.info(f"Final angle balance: {abs(port_angle - starboard_angle):.1f}° difference")
    logger.info(f"Confidence: {confidence}")
    
    # Log iteration summary
    logger.info("\n--- Iteration Summary ---")
    for hist in iteration_history:
        logger.info(f"Iteration {hist['iteration']}: Wind={hist['wind']:.1f}°, "
                   f"Port={hist['port_median']:.1f}° ({hist['port_count']}), "
                   f"Starboard={hist['starboard_median']:.1f}° ({hist['starboard_count']}), "
                   f"Imbalance={hist['imbalance']:.1f}°")
    
    # Return result
    return WindEstimate(
        direction=current_wind,
        confidence=confidence,
        user_provided=False,
        port_angle=port_angle,
        starboard_angle=starboard_angle,
        port_count=len(final_port),
        starboard_count=len(final_starboard)
    )