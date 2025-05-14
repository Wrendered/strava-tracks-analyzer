"""
Wind direction estimation algorithms.

This module contains algorithms for estimating wind direction based on sailing patterns.
It provides a unified API for different wind estimation methods with appropriate confidence levels.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from sklearn.cluster import KMeans

from core.wind.models import WindEstimate

logger = logging.getLogger(__name__)

def estimate_wind_direction_from_upwind_tacks(
    stretches: pd.DataFrame, 
    suspicious_angle_threshold: float = 20
) -> Optional[float]:
    """
    SIMPLIFIED algorithm to estimate wind direction based on upwind tacks.
    
    This method:
    1. Selects upwind segments (angle_to_wind < 90°)
    2. Filters out suspicious angles (<20° to wind)
    3. Gets average angles for port and starboard tacks
    4. Calculates wind direction from the bisector of the best port and starboard tracks
    
    Args:
        stretches: DataFrame with sailing segments
        suspicious_angle_threshold: Angles less than this are excluded (default: 20°)
    
    Returns:
        float: Estimated wind direction or None if insufficient data
    """
    # Must have required columns
    if stretches.empty or 'angle_to_wind' not in stretches.columns or 'tack' not in stretches.columns:
        return None
    
    # Step 1: Basic filtering - get upwind segments and remove suspicious angles
    upwind = stretches[
        (stretches['angle_to_wind'] < 90) & 
        (stretches['angle_to_wind'] >= suspicious_angle_threshold)
    ].copy()
    
    logger.info(f"Using {len(upwind)}/{len(stretches[stretches['angle_to_wind'] < 90])} " +
               f"upwind segments after removing angles < {suspicious_angle_threshold}°")
    
    # Need at least 3 segments for a valid calculation
    if len(upwind) < 3:
        return None
    
    # Step 2: Split by tack - no complex filtering
    port_upwind = upwind[upwind['tack'] == 'Port']
    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
    
    # Get current wind direction (for fallback)
    current_wind = stretches['wind_direction'].iloc[0] if 'wind_direction' in stretches.columns else None
    
    # Step 3: Simple average calculations - no weighted or statistical methods
    port_best_angle = None
    port_best_bearing = None
    if len(port_upwind) > 0:
        # For port tack, take best upwind angle (smallest angle to wind)
        port_sorted = port_upwind.sort_values('angle_to_wind')
        best_port = port_sorted.iloc[0]  # Just the single best angle
        port_best_angle = best_port['angle_to_wind']
        port_best_bearing = best_port['bearing']
    
    starboard_best_angle = None
    starboard_best_bearing = None
    if len(starboard_upwind) > 0:
        # For starboard tack, same approach
        starboard_sorted = starboard_upwind.sort_values('angle_to_wind')
        best_starboard = starboard_sorted.iloc[0]  # Just the single best angle
        starboard_best_angle = best_starboard['angle_to_wind']
        starboard_best_bearing = best_starboard['bearing']
    
    # Log what we found
    logger.info(f"Best port angle: {port_best_angle}, bearing: {port_best_bearing}")
    logger.info(f"Best starboard angle: {starboard_best_angle}, bearing: {starboard_best_bearing}")
    
    # Need at least one valid tack
    if port_best_angle is None and starboard_best_angle is None:
        return None
    
    # Step 4: Calculate wind direction - simplified approach
    # If we have both tacks, use the bisector
    if port_best_bearing is not None and starboard_best_bearing is not None:
        # Handle angle wrapping around 0/360
        if abs(port_best_bearing - starboard_best_bearing) > 180:
            if port_best_bearing < starboard_best_bearing:
                port_best_bearing += 360
            else:
                starboard_best_bearing += 360
        
        # Simple 50/50 average - no weighting
        bisector = (port_best_bearing + starboard_best_bearing) / 2
        if bisector >= 360:
            bisector -= 360
            
        # The wind direction is the bisector
        estimated_wind = bisector
        logger.info(f"Estimated wind from tack bisector: {estimated_wind:.1f}°")
        return estimated_wind
    
    # If just one tack, calculate from that one
    elif port_best_bearing is not None:
        # Wind = port bearing + port angle to wind
        estimated_wind = (port_best_bearing + port_best_angle) % 360
        logger.info(f"Estimated wind from port tack: {estimated_wind:.1f}°")
        return estimated_wind
        
    elif starboard_best_bearing is not None:
        # Wind = starboard bearing - starboard angle to wind
        estimated_wind = (starboard_best_bearing - starboard_best_angle) % 360
        logger.info(f"Estimated wind from starboard tack: {estimated_wind:.1f}°")
        return estimated_wind
    
    # Fallback to user-provided wind
    return current_wind

def estimate_balanced_wind_direction(
    stretches: pd.DataFrame, 
    user_wind_direction: float, 
    suspicious_angle_threshold: float = 20, 
    filter_suspicious: bool = True
) -> Optional[float]:
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
    
    Args:
        stretches: DataFrame with sailing segments (must have wind_direction and angle_to_wind)
        user_wind_direction: User's estimate of wind direction 
        suspicious_angle_threshold: Angles < this are excluded (usually 20°)
        filter_suspicious: Whether to filter out suspicious angles before estimation
    
    Returns:
        float: Estimated balanced wind direction or None if insufficient data
    """
    # Input validation
    if stretches is None or stretches.empty:
        logger.warning("Empty stretches DataFrame provided for wind estimation")
        return user_wind_direction
    
    try:
        # Normalize wind direction
        user_wind_direction = float(user_wind_direction) % 360
    except (ValueError, TypeError):
        logger.warning(f"Invalid wind direction value: {user_wind_direction}, defaulting to North (0°)")
        user_wind_direction = 0
    
    # Verify required columns exist
    required_columns = ['angle_to_wind', 'wind_direction', 'tack']
    if not all(col in stretches.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in stretches.columns]
        logger.warning(f"Missing required columns for wind estimation: {missing_cols}")
        return user_wind_direction
    
    try:
        # Step 1: Extract upwind segments (angles < 90° from user direction)
        upwind = stretches[stretches['angle_to_wind'] < 90].copy()
        
        # Step 2: Filter out suspicious angles (too close to wind) if requested
        if filter_suspicious:
            upwind = upwind[upwind['angle_to_wind'] >= suspicious_angle_threshold]
        
        # Check if we have enough data
        if len(upwind) < 3:
            logger.warning(f"Not enough upwind data points after filtering: {len(upwind)} segments")
            return user_wind_direction
        
        # Step 3: Split by tack
        port_tack = upwind[upwind['tack'] == 'Port']
        starboard_tack = upwind[upwind['tack'] == 'Starboard']
        
        # Log the tack distribution
        logger.debug(f"Upwind segments by tack: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
        
        # Need at least one segment in each tack for balance calculation
        if len(port_tack) == 0 or len(starboard_tack) == 0:
            logger.warning(f"Missing one tack: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
            return user_wind_direction
        
        # Step 4: Find best upwind angle cluster for each tack
        port_best_angle = None
        if len(port_tack) > 0:
            # Sort by closest angle to wind and by speed (prioritize faster segments)
            # This helps find the most efficient pointing angle, not just the closest
            if 'speed' in port_tack.columns:
                # Create a copy to avoid the SettingWithCopyWarning
                port_tack_copy = port_tack.copy()
                port_tack_copy.loc[:, 'efficiency_score'] = port_tack_copy['angle_to_wind'] - (port_tack_copy['speed'] / 5)
                port_sorted = port_tack_copy.sort_values('efficiency_score')
            else:
                port_sorted = port_tack.sort_values('angle_to_wind')
            
            # Get the closest angle to wind
            best_port = port_sorted.iloc[0]
            best_port_angle = best_port['angle_to_wind']
            
            # Select all port segments within 15° of the best angle
            cluster_range = min(15, max(5, len(port_tack) * 0.2))  # Adaptive range based on data
            port_cluster = port_tack[np.abs(port_tack['angle_to_wind'] - best_port_angle) <= cluster_range]
            
            # Take up to 5 best segments (or fewer if not enough in the cluster)
            max_segments = min(5, max(3, len(port_tack) // 3))  # Adaptive max segments
            if len(port_cluster) > max_segments:
                port_cluster = port_cluster.sort_values('angle_to_wind').iloc[:max_segments]
            
            # Calculate average angle for port cluster
            port_best_angle = port_cluster['angle_to_wind'].mean()
            logger.info(f"Port tack best angle: {port_best_angle:.1f}° (from {len(port_cluster)} segments)")
        
        starboard_best_angle = None
        if len(starboard_tack) > 0:
            # Sort by closest angle to wind and by speed (prioritize faster segments)
            if 'speed' in starboard_tack.columns:
                # Create a copy to avoid the SettingWithCopyWarning
                starboard_tack_copy = starboard_tack.copy()
                starboard_tack_copy.loc[:, 'efficiency_score'] = starboard_tack_copy['angle_to_wind'] - (starboard_tack_copy['speed'] / 5)
                starboard_sorted = starboard_tack_copy.sort_values('efficiency_score')
            else:
                starboard_sorted = starboard_tack.sort_values('angle_to_wind')
            
            # Get the closest angle to wind
            best_starboard = starboard_sorted.iloc[0]
            best_starboard_angle = best_starboard['angle_to_wind']
            
            # Select all starboard segments within adaptive range of the best angle
            cluster_range = min(15, max(5, len(starboard_tack) * 0.2))
            starboard_cluster = starboard_tack[np.abs(starboard_tack['angle_to_wind'] - best_starboard_angle) <= cluster_range]
            
            # Take up to 5 best segments (or fewer if not enough in the cluster)
            max_segments = min(5, max(3, len(starboard_tack) // 3))
            if len(starboard_cluster) > max_segments:
                starboard_cluster = starboard_cluster.sort_values('angle_to_wind').iloc[:max_segments]
            
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
        
    except Exception as e:
        logger.error(f"Error in balanced wind direction estimation: {e}")
        return user_wind_direction


def detect_and_remove_outliers(
    stretches: pd.DataFrame, 
    wind_direction: float, 
    suspicious_angle_threshold: float = 20
) -> Tuple[pd.DataFrame, bool]:
    """
    Detect improbable upwind angles based on the current wind direction.
    
    Args:
        stretches: DataFrame with sailing segments
        wind_direction: Current estimated wind direction
        suspicious_angle_threshold: Angles less than this are considered suspicious
    
    Returns:
        tuple: (filtered_stretches, outliers_found)
    """
    if stretches is None or stretches.empty:
        logger.warning("No stretches provided for outlier detection")
        return stretches, False
    
    try:
        # Normalize wind direction to 0-359 range
        wind_direction = float(wind_direction) % 360
        
        # Avoid circular import by using a deferred import within the function
        # Import from the package (which re-exports the original function)
        from core.segments import analyze_wind_angles as analyze_wind_angles_fn
        stretches_with_angles = analyze_wind_angles_fn(stretches.copy(), wind_direction)
        
        # Verify required columns exist
        required_columns = ['angle_to_wind', 'bearing']
        missing_columns = [col for col in required_columns if col not in stretches_with_angles.columns]
        if missing_columns:
            logger.warning(f"Missing required columns for outlier detection: {missing_columns}")
            return stretches, False
        
        # Find suspicious upwind angles (too close to wind)
        suspicious_segments = stretches_with_angles[
            (stretches_with_angles['angle_to_wind'] < suspicious_angle_threshold) &
            (stretches_with_angles['angle_to_wind'] < 90)  # Only consider upwind
        ]
        
        # If we found suspicious segments, filter them out
        if len(suspicious_segments) > 0:
            logger.info(f"Found {len(suspicious_segments)} suspicious upwind angles < {suspicious_angle_threshold}°")
            
            # Log details for debugging (limit to max 10 for cleaner logs)
            for idx, row in suspicious_segments.head(10).iterrows():
                logger.warning(f"Suspiciously small angle to wind detected: {row['angle_to_wind']:.1f}° " +
                             f"(bearing: {row['bearing']:.1f}°, wind: {wind_direction:.1f}°)")
            
            if len(suspicious_segments) > 10:
                logger.warning(f"... and {len(suspicious_segments) - 10} more suspicious angles")
            
            # Don't remove too many segments at once (max 25% of total)
            if len(suspicious_segments) > len(stretches) * 0.25:
                logger.warning(f"Too many suspicious segments ({len(suspicious_segments)} of {len(stretches)}). " +
                              f"Limiting to most extreme 25%")
                # Sort by angle and take only the most suspicious ones
                suspicious_segments = suspicious_segments.sort_values('angle_to_wind').head(int(len(stretches) * 0.25))
            
            # Remove suspicious segments
            filtered_stretches = stretches.drop(suspicious_segments.index)
            return filtered_stretches, True
            
        return stretches, False
        
    except Exception as e:
        logger.error(f"Error in outlier detection: {e}")
        return stretches, False


def iterative_wind_estimation(
    stretches: pd.DataFrame, 
    initial_wind_direction: float, 
    suspicious_angle_threshold: float = 20, 
    max_iterations: int = 3
) -> Optional[float]:
    """
    Iteratively estimate wind direction, removing suspicious angles in each iteration.
    
    Improved algorithm:
    1. First estimate wind direction using ALL segments (no suspicious angle filtering)
    2. Use this initial estimate to identify true outliers
    3. Then perform additional iterations with filtering if needed
    
    Args:
        stretches: DataFrame with sailing segments
        initial_wind_direction: Initial user-provided wind direction
        suspicious_angle_threshold: Angles less than this are considered suspicious
        max_iterations: Maximum number of iterations to perform
    
    Returns:
        float: Final estimated wind direction
    """
    # Input validation
    if stretches is None or stretches.empty:
        logger.warning("No stretches provided for wind estimation")
        return initial_wind_direction
        
    if initial_wind_direction is None:
        logger.warning("No initial wind direction provided, defaulting to North (0°)")
        initial_wind_direction = 0
    
    try:
        # Make a safe copy to avoid modifying the input
        current_stretches = stretches.copy()
        current_wind = float(initial_wind_direction) % 360  # Normalize to 0-359 range
        
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
    except Exception as e:
        logger.error(f"Error in initial wind estimation phase: {e}")
        return initial_wind_direction
    
    # Phase 2: Iterative refinement with outlier removal
    logger.info(f"Phase 2: Iterative refinement with outlier removal")
    
    try:
        for iteration in range(max_iterations):
            # Check for suspicious angles with the current wind direction
            try:
                filtered_stretches, outliers_found = detect_and_remove_outliers(
                    current_stretches, 
                    current_wind, 
                    suspicious_angle_threshold
                )
            except Exception as e:
                logger.error(f"Error detecting outliers in iteration {iteration+1}: {e}")
                break
            
            # If no outliers found, we're done
            if not outliers_found:
                logger.info(f"No outliers found, using wind direction: {current_wind:.1f}°")
                break
            
            # If too few segments left, stop iterating
            minimum_segments = max(5, len(current_stretches) * 0.1)  # At least 5 or 10% of original
            if len(filtered_stretches) < minimum_segments:
                logger.warning(f"Too few segments left after filtering ({len(filtered_stretches)}), using current wind")
                break
            
            # Continue with filtered stretches and re-estimate wind
            current_stretches = filtered_stretches
            logger.info(f"Iteration {iteration+1}: Continuing with {len(current_stretches)} segments after filtering outliers")
            
            # Now use balanced wind estimation WITH suspicious angle filtering
            try:
                refined_wind = estimate_balanced_wind_direction(
                    current_stretches,
                    current_wind,
                    suspicious_angle_threshold,
                    filter_suspicious=True  # Filter suspicious angles in subsequent passes
                )
            except Exception as e:
                logger.error(f"Error in wind estimation in iteration {iteration+1}: {e}")
                break
            
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
    
    except Exception as e:
        logger.error(f"Unexpected error in refinement phase: {e}")
        # We still return the best estimate we had before the error
    
    logger.info(f"Final wind direction after refinement: {current_wind:.1f}°")
    return current_wind