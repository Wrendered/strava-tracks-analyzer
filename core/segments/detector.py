"""
Segment detection algorithms.

This module contains functions for detecting consistent sailing segments in GPS track data.
Each function has a single responsibility and can be tested independently.
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Tuple, Dict, Any, Optional

from core.constants import FULL_CIRCLE_DEGREES, METERS_PER_SECOND_TO_KNOTS
from core.calculations import calculate_bearing, calculate_distance
from core.models.segment import Segment, segments_to_dataframe
from core.validation import (
    validate_gpx_dataframe, validate_parameter_ranges, 
    validate_and_clean_segments, safe_dataframe_operation,
    ValidationError
)

logger = logging.getLogger(__name__)


def calculate_point_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate bearing, distance, and duration for each point in the track.
    
    This is the first step in segment detection - it adds the basic metrics
    needed to identify consistent sailing angles.
    
    Args:
        df: DataFrame with 'latitude', 'longitude', 'time' columns
        
    Returns:
        DataFrame with added 'bearing', 'distance_m', 'duration_sec' columns
    """
    if len(df) < 2:
        logger.warning("Not enough points to calculate metrics")
        return df.copy()
    
    # Create a copy to avoid modifying the original
    result = df.copy()
    
    # Initialize lists for metrics
    bearings = []
    distances = []
    durations = []
    
    # Calculate metrics for each segment between consecutive points
    for i in range(len(df) - 1):
        lat1, lon1 = df.iloc[i]['latitude'], df.iloc[i]['longitude']
        lat2, lon2 = df.iloc[i+1]['latitude'], df.iloc[i+1]['longitude']
        
        # Calculate bearing and distance
        bearing = calculate_bearing(lat1, lon1, lat2, lon2)
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        
        bearings.append(bearing)
        distances.append(distance)
        
        # Calculate duration if time data is available
        if i > 0 and 'time' in df.columns and df.iloc[i]['time'] is not None and df.iloc[i-1]['time'] is not None:
            duration = (df.iloc[i]['time'] - df.iloc[i-1]['time']).total_seconds()
            durations.append(duration)
        else:
            durations.append(0)
    
    # Add one more value to match length of dataframe
    # Use the last calculated value (reasonable for the final point)
    bearings.append(bearings[-1] if bearings else 0)
    distances.append(distances[-1] if distances else 0)
    durations.append(durations[-1] if durations else 0)
    
    # Add metrics to the dataframe
    result['bearing'] = bearings
    result['distance_m'] = distances
    result['duration_sec'] = durations
    
    logger.debug(f"Calculated metrics for {len(result)} points")
    return result


def detect_angle_changes(df: pd.DataFrame, angle_tolerance: float) -> List[Tuple[int, int]]:
    """
    Detect where sailing angle changes exceed the tolerance.
    
    This identifies the boundaries of consistent angle stretches by finding
    where the bearing changes by more than the specified tolerance.
    
    Args:
        df: DataFrame with 'bearing' column
        angle_tolerance: Maximum bearing change allowed within a segment (degrees)
        
    Returns:
        List of (start_idx, end_idx) tuples for each consistent stretch
    """
    if len(df) < 2:
        return []
    
    stretches = []
    current_start = 0
    current_bearing = df.iloc[0]['bearing']
    
    for i in range(1, len(df)):
        current_point_bearing = df.iloc[i]['bearing']
        
        # Calculate the angular difference (handling 0/360 wraparound)
        angle_diff = min(
            (current_point_bearing - current_bearing) % FULL_CIRCLE_DEGREES,
            (current_bearing - current_point_bearing) % FULL_CIRCLE_DEGREES
        )
        
        if angle_diff > angle_tolerance:
            # End of current stretch
            stretches.append((current_start, i - 1))
            
            # Start new stretch
            current_start = i
            current_bearing = current_point_bearing
    
    # Add the final stretch
    if current_start < len(df) - 1:
        stretches.append((current_start, len(df) - 1))
    
    logger.debug(f"Detected {len(stretches)} angle-consistent stretches")
    return stretches


def build_segments(df: pd.DataFrame, stretches: List[Tuple[int, int]]) -> List[Segment]:
    """
    Build Segment objects from consistent angle stretches.
    
    This converts the raw stretch boundaries into properly structured
    Segment objects with all the calculated metrics.
    
    Args:
        df: DataFrame with calculated metrics
        stretches: List of (start_idx, end_idx) tuples
        
    Returns:
        List of Segment objects (before filtering)
    """
    segments = []
    
    for start_idx, end_idx in stretches:
        if start_idx >= end_idx:
            continue
            
        # Get the data for this stretch
        stretch_data = df.iloc[start_idx:end_idx + 1]
        
        if len(stretch_data) < 2:
            continue
        
        # Calculate segment metrics
        total_distance = stretch_data['distance_m'].sum()
        
        # Calculate duration
        start_time = stretch_data.iloc[0]['time']
        end_time = stretch_data.iloc[-1]['time']
        
        if start_time is not None and end_time is not None:
            total_duration = (end_time - start_time).total_seconds()
        else:
            total_duration = stretch_data['duration_sec'].sum()
        
        # Calculate average speed
        if total_duration > 0:
            avg_speed_ms = total_distance / total_duration
            avg_speed_knots = avg_speed_ms * METERS_PER_SECOND_TO_KNOTS
        else:
            avg_speed_knots = 0
        
        # Use the bearing from the start of the stretch
        bearing = stretch_data.iloc[0]['bearing']
        
        # Create segment object
        segment = Segment(
            start_time=start_time,
            end_time=end_time,
            start_idx=start_idx,
            end_idx=end_idx,
            bearing=bearing,
            distance=total_distance,
            duration=total_duration,
            avg_speed_knots=avg_speed_knots,
            point_count=len(stretch_data)
        )
        
        segments.append(segment)
    
    logger.debug(f"Built {len(segments)} segments from stretches")
    return segments


def filter_valid_segments(segments: List[Segment], 
                         min_distance_meters: float, 
                         min_duration_seconds: float) -> List[Segment]:
    """
    Filter segments to keep only those meeting minimum requirements.
    
    This removes segments that are too short in distance or duration
    to be considered valid sailing segments.
    
    Args:
        segments: List of segments to filter
        min_distance_meters: Minimum distance requirement
        min_duration_seconds: Minimum duration requirement
        
    Returns:
        List of valid segments
    """
    valid_segments = []
    
    for segment in segments:
        if (segment.distance >= min_distance_meters and 
            segment.duration >= min_duration_seconds):
            valid_segments.append(segment)
    
    logger.info(f"Filtered to {len(valid_segments)} valid segments " +
                f"(from {len(segments)} total) using min_distance={min_distance_meters}m, " +
                f"min_duration={min_duration_seconds}s")
    
    return valid_segments


def find_consistent_angle_stretches(df: pd.DataFrame, 
                                   angle_tolerance: float, 
                                   min_duration_seconds: float, 
                                   min_distance_meters: float) -> pd.DataFrame:
    """
    Find stretches of consistent sailing angle (REFACTORED VERSION).
    
    This is the main entry point for segment detection. It orchestrates
    the smaller, focused functions to detect and build sailing segments.
    
    Args:
        df: DataFrame with GPS track data
        angle_tolerance: Maximum bearing change allowed within a segment (degrees)
        min_duration_seconds: Minimum duration for valid segments (seconds)
        min_distance_meters: Minimum distance for valid segments (meters)
        
    Returns:
        DataFrame with detected segments
    """
    try:
        # Validate inputs
        validate_gpx_dataframe(df, "Segment detection input")
        validate_parameter_ranges(
            angle_tolerance=angle_tolerance,
            min_distance=min_distance_meters,
            min_duration=min_duration_seconds
        )
        
        logger.info(f"Starting segment detection with tolerance={angle_tolerance}°, " +
                    f"min_duration={min_duration_seconds}s, min_distance={min_distance_meters}m")
        
        # Check for minimum data points
        if len(df) < 2:
            logger.warning("Not enough GPS points for segment detection")
            return pd.DataFrame()
            
    except ValidationError as e:
        logger.error(f"Validation failed for segment detection: {e}")
        return pd.DataFrame()
    
    # Step 1: Calculate point metrics (bearing, distance, duration)
    df_with_metrics = calculate_point_metrics(df)
    
    # Step 2: Detect angle changes to find consistent stretches
    stretches = detect_angle_changes(df_with_metrics, angle_tolerance)
    
    if not stretches:
        logger.warning("No consistent angle stretches detected")
        return pd.DataFrame()
    
    # Step 3: Build segment objects from stretches
    segments = build_segments(df_with_metrics, stretches)
    
    if not segments:
        logger.warning("No segments could be built from stretches")
        return pd.DataFrame()
    
    # Step 4: Filter to keep only valid segments
    valid_segments = filter_valid_segments(segments, min_distance_meters, min_duration_seconds)
    
    if not valid_segments:
        logger.warning("No segments meet the minimum requirements")
        return pd.DataFrame()
    
    # Step 5: Convert to DataFrame for backward compatibility
    result_df = segments_to_dataframe(valid_segments)
    
    # Validate and clean the result
    cleaned_df = validate_and_clean_segments(result_df)
    
    logger.info(f"Successfully detected {len(valid_segments)} valid segments")
    return cleaned_df


def analyze_segment_distribution(segments: List[Segment]) -> Dict[str, Any]:
    """
    Analyze the distribution of detected segments.
    
    This provides useful statistics about the segments for debugging
    and quality assessment.
    
    Args:
        segments: List of detected segments
        
    Returns:
        Dictionary with distribution statistics
    """
    if not segments:
        return {}
    
    distances = [s.distance for s in segments]
    durations = [s.duration for s in segments]
    speeds = [s.avg_speed_knots for s in segments]
    
    stats = {
        'count': len(segments),
        'total_distance_km': sum(distances) / 1000,
        'total_duration_minutes': sum(durations) / 60,
        'avg_segment_distance_m': np.mean(distances),
        'avg_segment_duration_s': np.mean(durations),
        'avg_speed_knots': np.mean(speeds),
        'distance_range': (min(distances), max(distances)),
        'duration_range': (min(durations), max(durations)),
        'speed_range': (min(speeds), max(speeds))
    }
    
    return stats