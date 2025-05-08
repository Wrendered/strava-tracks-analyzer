"""
Simplified Wind Direction Estimation Algorithm.

This module contains the advanced but simplified approach to wind direction 
estimation that focuses on balancing the port and starboard tack angles.
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def estimate_balanced_wind_direction(stretches, user_wind_direction, suspicious_angle_threshold=20, filter_suspicious=True):
    """
    Estimate wind direction by balancing port and starboard upwind angles.
    
    Algorithm:
    1. Start with user-provided wind direction
    2. Select upwind tacks (angles < 90° from that direction)
    3. [Optional] Filter out suspicious angles (< suspicious_angle_threshold° to wind)
       - When filter_suspicious=False, we include ALL angles for initial estimation
       - When filter_suspicious=True, we filter out suspiciously small angles
    4. For both port & starboard:
       a. Find segment with angle CLOSEST to the wind
       b. Keep all segments within 15° of this best angle
       c. Calculate AVERAGE angle of these filtered segments
    5. Balance tack angles by adjusting wind direction:
       a. If port/starboard best angles differ, adjust wind direction by half the difference
       b. This makes port and starboard tacks equally efficient upwind
    6. Verify result is within 60° of user input; otherwise, return user input
    
    Parameters:
    - stretches: DataFrame with sailing segments (must have wind_direction and angle_to_wind)
    - user_wind_direction: User's estimate of wind direction 
    - suspicious_angle_threshold: Angles < this are excluded (usually 20°)
    - filter_suspicious: Whether to filter out suspicious angles before estimation
    
    Returns:
    - Estimated balanced wind direction (float) or None if insufficient data
    """
    if stretches.empty or 'angle_to_wind' not in stretches.columns or 'wind_direction' not in stretches.columns:
        logger.warning("Missing required columns for wind estimation")
        return user_wind_direction
    
    # Step 1: Extract upwind segments (angles < 90° from user direction)
    upwind = stretches[stretches['angle_to_wind'] < 90].copy()
    
    # Step 2: Filter out suspicious angles (too close to wind) if requested
    if filter_suspicious:
        upwind = upwind[upwind['angle_to_wind'] >= suspicious_angle_threshold]
    
    if len(upwind) < 3:
        logger.warning(f"Not enough upwind data points after filtering: {len(upwind)} segments")
        return user_wind_direction
    
    # Step 3: Split by tack
    port_tack = upwind[upwind['tack'] == 'Port']
    starboard_tack = upwind[upwind['tack'] == 'Starboard']
    
    # Need at least one segment in each tack for balance calculation
    if len(port_tack) == 0 or len(starboard_tack) == 0:
        logger.warning(f"Missing one tack: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
        return user_wind_direction
    
    # Step 4: Find best upwind angle cluster for each tack
    port_best_angle = None
    if len(port_tack) > 0:
        # Sort by closest angle to wind
        port_sorted = port_tack.sort_values('angle_to_wind')
        
        # Get the closest angle to wind
        best_port = port_sorted.iloc[0]
        best_port_angle = best_port['angle_to_wind']
        
        # Select all port segments within 15° of the best angle
        port_cluster = port_tack[np.abs(port_tack['angle_to_wind'] - best_port_angle) <= 15]
        
        # Take up to 5 best segments
        if len(port_cluster) > 5:
            port_cluster = port_cluster.sort_values('angle_to_wind').iloc[:5]
        
        # Calculate average angle for port cluster
        port_best_angle = port_cluster['angle_to_wind'].mean()
        logger.info(f"Port tack best angle: {port_best_angle:.1f}° (from {len(port_cluster)} segments)")
    
    starboard_best_angle = None
    if len(starboard_tack) > 0:
        # Sort by closest angle to wind
        starboard_sorted = starboard_tack.sort_values('angle_to_wind')
        
        # Get the closest angle to wind
        best_starboard = starboard_sorted.iloc[0]
        best_starboard_angle = best_starboard['angle_to_wind']
        
        # Select all starboard segments within 15° of the best angle
        starboard_cluster = starboard_tack[np.abs(starboard_tack['angle_to_wind'] - best_starboard_angle) <= 15]
        
        # Take up to 5 best segments
        if len(starboard_cluster) > 5:
            starboard_cluster = starboard_cluster.sort_values('angle_to_wind').iloc[:5]
        
        # Calculate average angle for starboard cluster
        starboard_best_angle = starboard_cluster['angle_to_wind'].mean()
        logger.info(f"Starboard tack best angle: {starboard_best_angle:.1f}° (from {len(starboard_cluster)} segments)")
    
    # Step 5: Calculate balanced wind direction
    if port_best_angle is None or starboard_best_angle is None:
        logger.warning("Couldn't determine both port and starboard best angles")
        return user_wind_direction
    
    # Calculate the difference between port and starboard best angles
    angle_difference = starboard_best_angle - port_best_angle
    
    # Adjust wind direction by half the difference to balance the angles
    # If port angle is smaller than starboard: DECREASE wind direction
    # If starboard angle is smaller than port: INCREASE wind direction
    wind_adjustment = angle_difference / 2.0
    
    # Apply adjustment to current wind direction
    adjusted_wind = (user_wind_direction - wind_adjustment) % 360
    
    # Log the adjustment
    logger.info(f"Angle difference: {angle_difference:.1f}°, Adjustment: {wind_adjustment:.1f}°")
    logger.info(f"Adjusted wind: {user_wind_direction:.1f}° → {adjusted_wind:.1f}°")
    
    # Step 6: Validate adjusted wind is within reasonable range (60°) of user input
    if abs(adjusted_wind - user_wind_direction) > 60:
        wrapped_diff = min(abs(adjusted_wind - user_wind_direction), 360 - abs(adjusted_wind - user_wind_direction))
        if wrapped_diff > 60:
            logger.warning(f"Adjusted wind {adjusted_wind:.1f}° too far from user input {user_wind_direction:.1f}°, using user input")
            return user_wind_direction
    
    return adjusted_wind


def detect_and_remove_outliers(stretches, wind_direction, suspicious_angle_threshold=20):
    """
    Detect improbable upwind angles based on the current wind direction.
    
    Parameters:
    - stretches: DataFrame with sailing segments
    - wind_direction: Current estimated wind direction
    - suspicious_angle_threshold: Angles less than this are considered suspicious
    
    Returns:
    - Tuple of (filtered_stretches, outliers_found)
    """
    if stretches.empty:
        return stretches, False
    
    # Ensure we have angles calculated for the current wind direction
    from utils.analysis import analyze_wind_angles
    stretches_with_angles = analyze_wind_angles(stretches.copy(), wind_direction)
    
    # Find suspicious upwind angles (too close to wind)
    suspicious_segments = stretches_with_angles[
        (stretches_with_angles['angle_to_wind'] < suspicious_angle_threshold) &
        (stretches_with_angles['angle_to_wind'] < 90)  # Only consider upwind
    ]
    
    # If we found suspicious segments, filter them out
    if len(suspicious_segments) > 0:
        logger.info(f"Found {len(suspicious_segments)} suspicious upwind angles < {suspicious_angle_threshold}°")
        
        for idx, row in suspicious_segments.iterrows():
            logger.warning(f"Suspiciously small angle to wind detected: {row['angle_to_wind']}° " +
                         f"(bearing: {row['bearing']}°, wind: {wind_direction}°)")
        
        # Remove suspicious segments
        filtered_stretches = stretches.drop(suspicious_segments.index)
        return filtered_stretches, True
    
    return stretches, False


def iterative_wind_estimation(stretches, initial_wind_direction, suspicious_angle_threshold=20, max_iterations=3):
    """
    Iteratively estimate wind direction, removing suspicious angles in each iteration.
    
    Improved algorithm:
    1. First estimate wind direction using ALL segments (no suspicious angle filtering)
    2. Use this initial estimate to identify true outliers
    3. Then perform additional iterations with filtering if needed
    
    Parameters:
    - stretches: DataFrame with sailing segments
    - initial_wind_direction: Initial user-provided wind direction
    - suspicious_angle_threshold: Angles less than this are considered suspicious
    - max_iterations: Maximum number of iterations to perform
    
    Returns:
    - Final estimated wind direction
    """
    current_stretches = stretches.copy()
    current_wind = initial_wind_direction
    
    # Phase 1: Initial estimation using ALL data points (no filtering)
    logger.info(f"Phase 1: Initial estimation using ALL data points with user wind {current_wind:.1f}°")
    
    # Run the first estimation WITHOUT filtering suspicious angles
    first_estimate = estimate_balanced_wind_direction(
        current_stretches,
        current_wind,
        suspicious_angle_threshold,
        filter_suspicious=False  # Do not filter suspicious angles in the first pass
    )
    
    # If the initial estimation failed, return the user input
    if first_estimate is None:
        logger.warning("Initial wind estimation failed, using user input")
        return current_wind
    
    # Update the current wind with the first estimate
    current_wind = first_estimate
    logger.info(f"Initial wind estimate (no filtering): {current_wind:.1f}°")
    
    # Phase 2: Iterative refinement with outlier removal
    logger.info(f"Phase 2: Iterative refinement with outlier removal")
    
    for iteration in range(max_iterations):
        # Check for suspicious angles with the current wind direction
        filtered_stretches, outliers_found = detect_and_remove_outliers(
            current_stretches, 
            current_wind, 
            suspicious_angle_threshold
        )
        
        # If no outliers found, we're done
        if not outliers_found:
            logger.info(f"No outliers found, using wind direction: {current_wind:.1f}°")
            break
        
        # If too few segments left, stop iterating
        if len(filtered_stretches) < 5:  # Require at least 5 segments
            logger.warning(f"Too few segments left after filtering ({len(filtered_stretches)}), using current wind")
            break
        
        # Continue with filtered stretches and re-estimate wind
        current_stretches = filtered_stretches
        logger.info(f"Iteration {iteration+1}: Continuing with {len(current_stretches)} segments after filtering outliers")
        
        # Now use balanced wind estimation WITH suspicious angle filtering
        refined_wind = estimate_balanced_wind_direction(
            current_stretches,
            current_wind,
            suspicious_angle_threshold,
            filter_suspicious=True  # Filter suspicious angles in subsequent passes
        )
        
        # If estimation failed, keep current estimate
        if refined_wind is None:
            logger.warning(f"Wind estimation failed in iteration {iteration+1}, using previous estimate")
            break
        
        # Update current values
        previous_wind = current_wind
        current_wind = refined_wind
        
        # Check for convergence - if wind direction stabilized, stop iterating
        if abs(current_wind - previous_wind) < 1.0:
            logger.info(f"Wind direction stabilized at {current_wind:.1f}°, stopping iterations")
            break
    
    logger.info(f"Final wind direction after refinement: {current_wind:.1f}°")
    return current_wind