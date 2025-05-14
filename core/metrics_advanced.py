"""
Advanced metrics calculations with distance weighting.

This module extends the basic metrics module with more sophisticated algorithms
that properly weight segments by distance and quality for more accurate
wind direction estimation and VMG calculations.
"""

from core.wind.models import WindEstimate

import pandas as pd
import numpy as np
import math
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

logger = logging.getLogger(__name__)

def calculate_segment_quality_score(segments: pd.DataFrame) -> pd.Series:
    """
    Calculate a quality score for each segment based on multiple factors.
    
    The quality score combines:
    - Distance (50% weight): Longer segments are more reliable
    - Speed (30% weight): Faster segments often have more consistent angles
    - Duration (20% weight): Longer duration segments are more stable
    
    Args:
        segments: DataFrame with sailing segments containing at minimum 'distance'
                 and optionally 'speed' and 'duration' columns
    
    Returns:
        pd.Series: Quality score for each segment (0-1 range)
    """
    if segments.empty:
        return pd.Series()
    
    # Initialize with base value
    quality_score = pd.Series(0.5, index=segments.index)
    
    # Distance is the primary factor (50%)
    if 'distance' in segments.columns:
        max_distance = segments['distance'].max()
        if max_distance > 0:
            normalized_distance = segments['distance'] / max_distance
            # Distance contributes 50% to the score
            quality_score = 0.5 * normalized_distance
        else:
            # If all distances are 0, assign equal weight
            quality_score = pd.Series(0.5, index=segments.index)
    
    # Speed factor (30%) if available
    if 'speed' in segments.columns:
        max_speed = segments['speed'].max()
        if max_speed > 0:
            normalized_speed = segments['speed'] / max_speed
            # Speed contributes 30% to quality score
            quality_score += 0.3 * normalized_speed
    
    # Duration factor (20%) if available
    if 'duration' in segments.columns:
        max_duration = segments['duration'].max()
        if max_duration > 0:
            normalized_duration = segments['duration'] / max_duration
            # Duration contributes 20% to quality score
            quality_score += 0.2 * normalized_duration
    
    return quality_score

def calculate_vmg_upwind(
    upwind_segments: pd.DataFrame,
    angle_range: float = 20,
    min_segment_distance: float = 50
) -> Optional[float]:
    """
    Calculate improved VMG upwind with distance weighting.
    
    This improved algorithm:
    1. Filters segments by minimum distance
    2. Weights angles by distance when finding the best upwind angle
    3. Includes only segments within a specified range of the best angle
    4. Calculates VMG as distance-weighted average of all qualifying segments
    
    Args:
        upwind_segments: DataFrame with upwind sailing segments
        angle_range: Range around best angle to include (in degrees)
        min_segment_distance: Minimum segment distance to consider (in meters)
    
    Returns:
        float: Distance-weighted VMG upwind or None if insufficient data
    """
    upwind_vmg = None
    
    if upwind_segments.empty:
        return None
    
    try:
        # Step 1: Filter by minimum distance
        filtered_upwind = upwind_segments[upwind_segments['distance'] >= min_segment_distance]
        
        # If no segments meet the minimum distance requirement, fall back to all segments
        if filtered_upwind.empty:
            logger.warning(f"No upwind segments meet the {min_segment_distance}m minimum distance. Using all upwind segments.")
            filtered_upwind = upwind_segments
        
        if not filtered_upwind.empty:
            # Step 2: Find best upwind angle weighted by distance
            # For best upwind angle, we use a weighted percentile approach
            # This balances between the absolute closest-to-wind angle and segment quality
            
            # Calculate the quality score for each segment
            quality_scores = calculate_segment_quality_score(filtered_upwind)
            
            # The segment with the highest quality score and smallest angle is our "best" angle
            # We combine quality and angle with a weighted approach
            filtered_upwind['combined_score'] = filtered_upwind['angle_to_wind'] - (quality_scores * 10)
            best_segment = filtered_upwind.sort_values('combined_score').iloc[0]
            weighted_best_angle = best_segment['angle_to_wind']
            
            logger.info(f"Best upwind angle (distance-weighted): {weighted_best_angle:.1f}°")
            
            # Step 3: Filter to segments within range of best angle
            max_angle_threshold = min(weighted_best_angle + angle_range, 90)
            angle_filtered = filtered_upwind[filtered_upwind['angle_to_wind'] <= max_angle_threshold]
            
            if not angle_filtered.empty:
                # Step 4: Calculate VMG for each segment
                angle_filtered = angle_filtered.copy()  # Make a copy to avoid SettingWithCopyWarning
                angle_filtered['vmg'] = angle_filtered.apply(
                    lambda row: row['speed'] * math.cos(math.radians(row['angle_to_wind'])), axis=1
                )
                
                # Log individual VMGs for debugging
                logger.debug(f"Calculating VMG from {len(angle_filtered)} segments with angles: " +
                           f"{angle_filtered['angle_to_wind'].tolist()}")
                logger.debug(f"Individual VMGs: {angle_filtered['vmg'].tolist()}")
                
                # Step 5: Weight by distance
                vmg_values = angle_filtered['vmg'].values
                distance_weights = angle_filtered['distance'].values
                
                # Calculate weighted average VMG
                total_distance = angle_filtered['distance'].sum()
                if total_distance > 0:
                    upwind_vmg = np.average(vmg_values, weights=distance_weights)
                    logger.info(f"Calculated VMG upwind: {upwind_vmg:.2f} knots (from {len(angle_filtered)} segments)")
    
    except Exception as e:
        logger.error(f"Error calculating upwind VMG: {e}")
    
    return upwind_vmg

def calculate_vmg_downwind(
    downwind_segments: pd.DataFrame,
    angle_range: float = 20,
    min_segment_distance: float = 50
) -> Optional[float]:
    """
    Calculate improved VMG downwind with distance weighting.
    
    Similar to upwind VMG but optimized for downwind segments.
    For downwind, we want the largest angle from wind and highest speed.
    
    Args:
        downwind_segments: DataFrame with downwind sailing segments
        angle_range: Range around best angle to include (in degrees)
        min_segment_distance: Minimum segment distance to consider (in meters)
    
    Returns:
        float: Distance-weighted VMG downwind or None if insufficient data
    """
    downwind_vmg = None
    
    if downwind_segments.empty:
        return None
    
    try:
        # Step 1: Filter by minimum distance
        filtered_downwind = downwind_segments[downwind_segments['distance'] >= min_segment_distance]
        
        # If no segments meet the minimum distance requirement, fall back to all segments
        if filtered_downwind.empty:
            logger.warning(f"No downwind segments meet the {min_segment_distance}m minimum distance. Using all downwind segments.")
            filtered_downwind = downwind_segments
        
        if not filtered_downwind.empty:
            # Step 2: Find best downwind angle weighted by distance
            # For downwind, we want largest angle_to_wind (closest to 180°)
            
            # Calculate the quality score for each segment
            quality_scores = calculate_segment_quality_score(filtered_downwind)
            
            # For downwind, higher angle is better, so we reverse the order with negative sign
            filtered_downwind['combined_score'] = -filtered_downwind['angle_to_wind'] - (quality_scores * 10)
            best_segment = filtered_downwind.sort_values('combined_score').iloc[0]
            weighted_best_angle = best_segment['angle_to_wind']
            
            logger.info(f"Best downwind angle (distance-weighted): {weighted_best_angle:.1f}°")
            
            # Step 3: Filter to segments within range of best angle
            # For downwind, we want angles LARGER than (best_angle - range)
            min_angle_threshold = max(weighted_best_angle - angle_range, 90)
            angle_filtered = filtered_downwind[filtered_downwind['angle_to_wind'] >= min_angle_threshold]
            
            if not angle_filtered.empty:
                # Step 4: Calculate VMG for each segment
                angle_filtered = angle_filtered.copy()  # Make a copy to avoid SettingWithCopyWarning
                angle_filtered['vmg'] = angle_filtered.apply(
                    lambda row: row['speed'] * math.cos(math.radians(180 - row['angle_to_wind'])), axis=1
                )
                
                # Step 5: Weight by distance
                vmg_values = angle_filtered['vmg'].values
                distance_weights = angle_filtered['distance'].values
                
                # Calculate weighted average VMG
                total_distance = angle_filtered['distance'].sum()
                if total_distance > 0:
                    downwind_vmg = np.average(vmg_values, weights=distance_weights)
                    logger.info(f"Calculated VMG downwind: {downwind_vmg:.2f} knots (from {len(angle_filtered)} segments)")
    
    except Exception as e:
        logger.error(f"Error calculating downwind VMG: {e}")
    
    return downwind_vmg

def estimate_wind_direction_weighted(
    stretches: pd.DataFrame,
    user_wind_direction: float,
    suspicious_angle_threshold: float = 20,
    min_segment_distance: float = 50
) -> WindEstimate:
    """
    Estimate wind direction by balancing port and starboard tacks with distance weighting.
    
    This enhanced algorithm:
    1. Filters segments by minimum distance
    2. Weights segments by distance when calculating average angles
    3. Balances port and starboard tacks based on their relative distances
    4. Returns a WindEstimate object with confidence score based on data quality
    
    Args:
        stretches: DataFrame with sailing segments
        user_wind_direction: User-provided initial wind direction (degrees)
        suspicious_angle_threshold: Angles less than this are considered suspicious (degrees)
        min_segment_distance: Minimum segment distance to consider (meters)
    
    Returns:
        WindEstimate: Wind direction estimate with metadata
    """
    # Initialize result with user-provided value
    result = WindEstimate(
        direction=user_wind_direction,
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
    
    # Ensure we have required columns
    required_columns = ['angle_to_wind', 'tack', 'distance', 'bearing']
    if not all(col in stretches.columns for col in required_columns):
        missing = [col for col in required_columns if col not in stretches.columns]
        logger.warning(f"Missing required columns for wind estimation: {missing}")
        return result
    
    try:
        # Normalize user wind direction
        user_wind_direction = float(user_wind_direction) % 360
        
        # Step 1: Filter upwind segments (angle_to_wind < 90°)
        upwind = stretches[stretches['angle_to_wind'] < 90].copy()
        
        # Step 2: Filter out suspiciously small angles to wind
        if suspicious_angle_threshold > 0:
            upwind = upwind[upwind['angle_to_wind'] >= suspicious_angle_threshold]
            logger.info(f"Filtered to {len(upwind)} upwind segments with angles >= {suspicious_angle_threshold}°")
        
        # Step 3: Apply minimum distance filter
        if min_segment_distance > 0:
            upwind_all = upwind.copy()  # Keep a copy before filtering
            upwind = upwind[upwind['distance'] >= min_segment_distance]
            logger.info(f"Filtered to {len(upwind)} upwind segments with distance >= {min_segment_distance}m")
            
            # If too few segments remain after filtering, fall back to all segments
            if len(upwind) < 3 and len(upwind_all) >= 3:
                logger.warning(f"Too few segments ({len(upwind)}) meet distance criteria. Using all upwind segments.")
                upwind = upwind_all
        
        # Need at least 3 segments for reliable estimation
        if len(upwind) < 3:
            logger.warning(f"Insufficient upwind segments ({len(upwind)}) for reliable wind estimation")
            return result
        
        # Step 4: Split by tack
        port_tack = upwind[upwind['tack'] == 'Port']
        starboard_tack = upwind[upwind['tack'] == 'Starboard']
        
        # Need at least one segment in each tack for balanced estimation
        has_both_tacks = len(port_tack) > 0 and len(starboard_tack) > 0
        
        if not has_both_tacks:
            logger.warning(f"Missing one tack: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
            # We'll still try to estimate with one tack, but confidence will be low
        
        # Step 5: Calculate weighted average angles for each tack
        port_angle = None
        port_total_distance = 0
        if len(port_tack) > 0:
            # Calculate quality scores
            port_quality = calculate_segment_quality_score(port_tack)
            
            # Calculate combined weights (distance * quality)
            port_weights = port_tack['distance'].values * port_quality.values
            port_angles = port_tack['angle_to_wind'].values
            
            # Calculate weighted average angle
            port_angle = np.average(port_angles, weights=port_weights)
            port_total_distance = port_tack['distance'].sum()
            
            logger.info(f"Port tack weighted average angle: {port_angle:.1f}° (from {len(port_tack)} segments)")
        
        starboard_angle = None
        starboard_total_distance = 0
        if len(starboard_tack) > 0:
            # Calculate quality scores
            starboard_quality = calculate_segment_quality_score(starboard_tack)
            
            # Calculate combined weights (distance * quality)
            starboard_weights = starboard_tack['distance'].values * starboard_quality.values
            starboard_angles = starboard_tack['angle_to_wind'].values
            
            # Calculate weighted average angle
            starboard_angle = np.average(starboard_angles, weights=starboard_weights)
            starboard_total_distance = starboard_tack['distance'].sum()
            
            logger.info(f"Starboard tack weighted average angle: {starboard_angle:.1f}° (from {len(starboard_tack)} segments)")
        
        # Step 6: Use the angles to estimate wind direction
        estimated_wind = None
        tack_difference = None
        
        if has_both_tacks:
            # Calculate the average angle weighted by total distance of each tack
            total_distance = port_total_distance + starboard_total_distance
            port_weight = port_total_distance / total_distance
            starboard_weight = starboard_total_distance / total_distance
            
            # Calculate weighted average angle
            weighted_avg_angle = (port_angle * port_weight + starboard_angle * starboard_weight)
            
            # Calculate angle difference between tacks
            tack_difference = abs(port_angle - starboard_angle)
            
            # Apply the balanced approach: calculate port-starboard imbalance
            angle_difference = starboard_angle - port_angle
            
            # Apply weighted adjustment to user wind direction
            wind_adjustment = angle_difference / 2.0
            estimated_wind = (user_wind_direction - wind_adjustment) % 360
            
            logger.info(f"Estimated wind: {estimated_wind:.1f}° (adjustment: {wind_adjustment:.1f}°)")
            
            # Confidence level based on data quality and tack difference
            confidence = "medium"
            
            # Higher confidence if:
            # 1. We have several segments in each tack
            # 2. Port and starboard angles are reasonably similar
            # 3. We have significant total distance
            if (len(port_tack) >= 3 and len(starboard_tack) >= 3 and
                tack_difference < 20 and total_distance > 500):
                confidence = "high"
            
            # Lower confidence if:
            # 1. Port and starboard angles differ greatly
            # 2. We have few segments in either tack
            if tack_difference > 45 or (len(port_tack) < 2 or len(starboard_tack) < 2):
                confidence = "low"
        else:
            # Single-tack estimation (less reliable)
            confidence = "low"
            
            if port_angle is not None:
                # For port tack, wind = bearing + angle_to_wind
                port_bearings = port_tack['bearing'].values
                # Take the weighted average bearing
                port_bearing = np.average(port_bearings, weights=port_tack['distance'].values)
                estimated_wind = (port_bearing + port_angle) % 360
                logger.info(f"Estimated wind from port tack only: {estimated_wind:.1f}°")
            
            elif starboard_angle is not None:
                # For starboard tack, wind = bearing - angle_to_wind
                starboard_bearings = starboard_tack['bearing'].values
                # Take the weighted average bearing
                starboard_bearing = np.average(starboard_bearings, weights=starboard_tack['distance'].values)
                estimated_wind = (starboard_bearing - starboard_angle) % 360
                logger.info(f"Estimated wind from starboard tack only: {estimated_wind:.1f}°")
        
        # If we have an estimate, return it
        if estimated_wind is not None:
            result = WindEstimate(
                direction=estimated_wind,
                confidence=confidence,
                user_provided=False,
                port_angle=port_angle,
                starboard_angle=starboard_angle,
                port_count=len(port_tack),
                starboard_count=len(starboard_tack)
            )
    
    except Exception as e:
        logger.error(f"Error in wind direction estimation: {e}")
    
    return result