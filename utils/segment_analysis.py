"""
Segment analysis utilities for debugging and quality checks.

This module contains tools to examine segments, detect anomalies,
and analyze patterns in the data.
"""

import pandas as pd
import numpy as np
import logging
import math
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

def find_nearby_segments(
    segments: pd.DataFrame,
    distance_threshold: float = 10.0, # meters
    time_threshold: float = 5.0 # seconds
) -> pd.DataFrame:
    """
    Find segments that are close to each other in time or space but have different properties.
    
    This can help identify segments that should possibly be merged or segments with inconsistent
    angles that might be due to GPS errors or algorithm issues.
    
    Args:
        segments: DataFrame with sailing segments
        distance_threshold: Distance threshold for considering segments nearby (meters)
        time_threshold: Time threshold for considering segments nearby (seconds)
        
    Returns:
        DataFrame: Pairs of segments that are nearby but have different properties
    """
    if segments.empty or len(segments) < 2:
        return pd.DataFrame()
    
    nearby_pairs = []
    
    # Sort segments by start index
    sorted_segments = segments.sort_values('start_idx')
    
    # Look for adjacent segments
    for i in range(len(sorted_segments) - 1):
        current = sorted_segments.iloc[i]
        next_segment = sorted_segments.iloc[i+1]
        
        # Check if segments are adjacent in the track
        if next_segment['start_idx'] - current['end_idx'] <= 2:
            # Calculate difference in bearing/angle
            bearing_diff = min(abs(next_segment['bearing'] - current['bearing']), 
                             360 - abs(next_segment['bearing'] - current['bearing']))
            
            angle_diff = abs(next_segment['angle_to_wind'] - current['angle_to_wind'])
            
            # Calculate distance between end of current and start of next
            if 'latitude' in segments.columns and 'longitude' in segments.columns:
                from utils.geo import calculate_distance
                distance = calculate_distance(
                    current['end_latitude'], current['end_longitude'],
                    next_segment['start_latitude'], next_segment['start_longitude']
                )
            else:
                distance = None
                
            # Calculate time difference if timestamps available
            if 'start_time' in segments.columns and 'end_time' in segments.columns:
                time_diff = (next_segment['start_time'] - current['end_time']).total_seconds()
            else:
                time_diff = None
                
            # If segments have significantly different properties but are nearby
            if (bearing_diff > 20 or angle_diff > 20) and \
               ((distance is not None and distance < distance_threshold) or \
                (time_diff is not None and time_diff < time_threshold)):
                
                nearby_pairs.append({
                    'segment1_idx': current.name,
                    'segment2_idx': next_segment.name,
                    'bearing_diff': bearing_diff,
                    'angle_diff': angle_diff,
                    'distance': distance,
                    'time_diff': time_diff,
                    'segment1_bearing': current['bearing'],
                    'segment2_bearing': next_segment['bearing'],
                    'segment1_angle': current['angle_to_wind'] if 'angle_to_wind' in current else None,
                    'segment2_angle': next_segment['angle_to_wind'] if 'angle_to_wind' in next_segment else None,
                    'segment1_distance': current['distance'] if 'distance' in current else None,
                    'segment2_distance': next_segment['distance'] if 'distance' in next_segment else None,
                })
                
    return pd.DataFrame(nearby_pairs)

def analyze_segment_quality(segments: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze the quality of segments based on various criteria.
    
    Assigns a quality score to each segment based on:
    - Length of segment
    - Consistency of bearing
    - GPS accuracy (if available)
    - Speed consistency
    
    Args:
        segments: DataFrame with sailing segments
        
    Returns:
        DataFrame: Segments with added quality metrics
    """
    if segments.empty:
        return segments
    
    # Create a copy to avoid modifying the original
    result = segments.copy()
    
    # Calculate a basic quality score based on segment distance
    max_distance = result['distance'].max()
    if max_distance > 0:
        result['distance_score'] = result['distance'] / max_distance
    else:
        result['distance_score'] = 0
        
    # Assign overall quality score
    # For now, just use distance as the primary factor
    result['quality_score'] = result['distance_score']
    
    return result

def detect_suspicious_segments(
    segments: pd.DataFrame,
    min_angle_to_wind: float = 20.0,
    min_segment_length: float = 30.0,
    max_bearing_change: float = 45.0
) -> pd.DataFrame:
    """
    Detect suspicious segments that may be due to GPS errors or other issues.
    
    Flags segments as suspicious if:
    - They have an unrealistically small angle to wind
    - They are very short but have a large bearing change from adjacent segments
    - They have inconsistent bearings internally
    
    Args:
        segments: DataFrame with sailing segments
        min_angle_to_wind: Minimum physically realistic angle to wind (degrees)
        min_segment_length: Minimum segment length to be considered reliable (meters)
        max_bearing_change: Maximum realistic bearing change between adjacent segments (degrees)
        
    Returns:
        DataFrame: Segments with added 'suspicious' flag and reason
    """
    if segments.empty:
        return segments
    
    # Create a copy to avoid modifying the original
    result = segments.copy()
    
    # Add suspicious flag (initialized to False)
    result['suspicious'] = False
    result['suspicious_reason'] = None
    
    # Flag 1: Unrealistically small angle to wind
    if 'angle_to_wind' in result.columns:
        small_angle_mask = result['angle_to_wind'] < min_angle_to_wind
        result.loc[small_angle_mask, 'suspicious'] = True
        result.loc[small_angle_mask, 'suspicious_reason'] = f"Angle to wind < {min_angle_to_wind}°"
    
    # Flag 2: Very short segment
    short_segment_mask = result['distance'] < min_segment_length
    result.loc[short_segment_mask, 'suspicious'] = True
    result.loc[short_segment_mask, 'suspicious_reason'] = f"Segment too short (< {min_segment_length}m)"
    
    # Find nearby segments with large bearing changes
    nearby_segments = find_nearby_segments(segments)
    
    if not nearby_segments.empty:
        for _, row in nearby_segments.iterrows():
            if row['bearing_diff'] > max_bearing_change:
                # Flag both segments as suspicious
                result.loc[row['segment1_idx'], 'suspicious'] = True
                result.loc[row['segment2_idx'], 'suspicious'] = True
                
                # Add reason
                current_reason = result.loc[row['segment1_idx'], 'suspicious_reason']
                if pd.isna(current_reason) or current_reason is None:
                    result.loc[row['segment1_idx'], 'suspicious_reason'] = f"Large bearing change ({row['bearing_diff']:.1f}°)"
                else:
                    result.loc[row['segment1_idx'], 'suspicious_reason'] += f"; Large bearing change ({row['bearing_diff']:.1f}°)"
                    
                current_reason = result.loc[row['segment2_idx'], 'suspicious_reason']
                if pd.isna(current_reason) or current_reason is None:
                    result.loc[row['segment2_idx'], 'suspicious_reason'] = f"Large bearing change ({row['bearing_diff']:.1f}°)"
                else:
                    result.loc[row['segment2_idx'], 'suspicious_reason'] += f"; Large bearing change ({row['bearing_diff']:.1f}°)"
    
    return result