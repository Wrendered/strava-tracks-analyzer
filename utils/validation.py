"""
Input validation helpers.

This module contains helper functions for validating user input
and parameters.
"""

from typing import Any, Optional, Dict, List, Union, Tuple
import pandas as pd

def validate_wind_direction(wind_direction: Any) -> Tuple[float, bool]:
    """
    Validate and normalize wind direction input.
    
    Args:
        wind_direction: Wind direction value to validate
        
    Returns:
        tuple: (normalized_direction, is_valid)
    """
    try:
        value = float(wind_direction)
        # Normalize to 0-359 range
        normalized = value % 360
        return normalized, True
    except (ValueError, TypeError):
        return 0.0, False

def validate_gpx_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
    """
    Validate GPX data for required columns and structure.
    
    Args:
        data: DataFrame with GPX data
        
    Returns:
        tuple: (validated_data, is_valid)
    """
    is_valid = True
    
    # Check if the DataFrame is empty
    if data.empty:
        return data, False
    
    # Required columns
    required_columns = ['latitude', 'longitude']
    
    # Check required columns
    for col in required_columns:
        if col not in data.columns:
            is_valid = False
            break
    
    # Check data types
    if is_valid:
        try:
            # Ensure latitude and longitude are numeric
            data['latitude'] = pd.to_numeric(data['latitude'])
            data['longitude'] = pd.to_numeric(data['longitude'])
        except (ValueError, TypeError):
            is_valid = False
    
    # Validate time column if present
    if is_valid and 'time' in data.columns:
        # Ensure time is datetime
        try:
            data['time'] = pd.to_datetime(data['time'])
        except (ValueError, TypeError):
            # If conversion fails, drop the time column
            data = data.drop(columns=['time'])
            is_valid = False
    
    return data, is_valid

def validate_segment_params(
    angle_tolerance: Any, 
    min_duration: Any, 
    min_distance: Any, 
    min_speed: Any
) -> Dict[str, Union[float, bool]]:
    """
    Validate segment detection parameters.
    
    Args:
        angle_tolerance: Maximum angle variation in degrees
        min_duration: Minimum duration in seconds
        min_distance: Minimum distance in meters
        min_speed: Minimum speed in knots
        
    Returns:
        dict: Dictionary with validated parameters and validation status
    """
    result = {
        'is_valid': True,
        'angle_tolerance': 20.0,
        'min_duration': 20.0,
        'min_distance': 100.0,
        'min_speed': 10.0
    }
    
    # Validate angle_tolerance
    try:
        val = float(angle_tolerance)
        if 0 < val <= 180:
            result['angle_tolerance'] = val
        else:
            result['is_valid'] = False
    except (ValueError, TypeError):
        result['is_valid'] = False
    
    # Validate min_duration
    try:
        val = float(min_duration)
        if val >= 0:
            result['min_duration'] = val
        else:
            result['is_valid'] = False
    except (ValueError, TypeError):
        result['is_valid'] = False
    
    # Validate min_distance
    try:
        val = float(min_distance)
        if val >= 0:
            result['min_distance'] = val
        else:
            result['is_valid'] = False
    except (ValueError, TypeError):
        result['is_valid'] = False
    
    # Validate min_speed
    try:
        val = float(min_speed)
        if val >= 0:
            result['min_speed'] = val
        else:
            result['is_valid'] = False
    except (ValueError, TypeError):
        result['is_valid'] = False
    
    return result