"""
Input validation utilities for core functions.

This module provides comprehensive validation functions to ensure data integrity
and prevent errors throughout the application.
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Optional, Union, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_gpx_dataframe(df: pd.DataFrame, context: str = "GPX data") -> pd.DataFrame:
    """
    Validate a GPX DataFrame has required columns and valid data.
    
    Args:
        df: DataFrame to validate
        context: Context description for error messages
        
    Returns:
        Validated DataFrame
        
    Raises:
        ValidationError: If validation fails
    """
    if df is None:
        raise ValidationError(f"{context}: DataFrame is None")
    
    if df.empty:
        raise ValidationError(f"{context}: DataFrame is empty")
    
    # Required columns for basic GPX processing
    required_columns = ['latitude', 'longitude']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValidationError(f"{context}: Missing required columns: {missing_columns}")
    
    # Validate coordinate ranges
    if not df['latitude'].between(-90, 90).all():
        invalid_count = (~df['latitude'].between(-90, 90)).sum()
        raise ValidationError(f"{context}: {invalid_count} invalid latitude values (must be -90 to 90)")
    
    if not df['longitude'].between(-180, 180).all():
        invalid_count = (~df['longitude'].between(-180, 180)).sum()
        raise ValidationError(f"{context}: {invalid_count} invalid longitude values (must be -180 to 180)")
    
    # Check for NaN values in critical columns
    for col in required_columns:
        if df[col].isna().any():
            nan_count = df[col].isna().sum()
            logger.warning(f"{context}: {nan_count} NaN values in {col} column")
    
    # Validate minimum data points
    if len(df) < 2:
        raise ValidationError(f"{context}: Need at least 2 data points for analysis, got {len(df)}")
    
    logger.debug(f"{context}: Validation passed for {len(df)} data points")
    return df


def validate_segments_dataframe(df: pd.DataFrame, context: str = "Segments") -> pd.DataFrame:
    """
    Validate a segments DataFrame has required columns and valid data.
    
    Args:
        df: Segments DataFrame to validate
        context: Context description for error messages
        
    Returns:
        Validated DataFrame
        
    Raises:
        ValidationError: If validation fails
    """
    if df is None:
        raise ValidationError(f"{context}: DataFrame is None")
    
    if df.empty:
        return df  # Empty segments is acceptable
    
    # Required columns for segment analysis
    required_columns = ['distance', 'duration', 'bearing']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValidationError(f"{context}: Missing required columns: {missing_columns}")
    
    # Validate numeric ranges
    if (df['distance'] < 0).any():
        invalid_count = (df['distance'] < 0).sum()
        raise ValidationError(f"{context}: {invalid_count} negative distance values")
    
    if (df['duration'] < 0).any():
        invalid_count = (df['duration'] < 0).sum()
        raise ValidationError(f"{context}: {invalid_count} negative duration values")
    
    if not df['bearing'].between(0, 360).all():
        invalid_count = (~df['bearing'].between(0, 360)).sum()
        raise ValidationError(f"{context}: {invalid_count} invalid bearing values (must be 0-360)")
    
    # Check for suspicious data
    if 'avg_speed_knots' in df.columns:
        max_reasonable_speed = 100  # knots
        if (df['avg_speed_knots'] > max_reasonable_speed).any():
            fast_count = (df['avg_speed_knots'] > max_reasonable_speed).sum()
            logger.warning(f"{context}: {fast_count} segments with speed > {max_reasonable_speed} knots")
    
    logger.debug(f"{context}: Validation passed for {len(df)} segments")
    return df


def validate_wind_direction(wind_direction: Union[int, float, str], context: str = "Wind direction") -> float:
    """
    Validate and normalize wind direction.
    
    Args:
        wind_direction: Wind direction value to validate
        context: Context description for error messages
        
    Returns:
        Normalized wind direction (0-359.99)
        
    Raises:
        ValidationError: If validation fails
    """
    if wind_direction is None:
        raise ValidationError(f"{context}: Value is None")
    
    try:
        wind_float = float(wind_direction)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{context}: Cannot convert to float: {wind_direction}") from e
    
    if np.isnan(wind_float) or np.isinf(wind_float):
        raise ValidationError(f"{context}: Invalid value: {wind_float}")
    
    # Normalize to 0-359.99 range
    normalized = wind_float % 360.0
    
    logger.debug(f"{context}: {wind_direction} → {normalized}")
    return normalized


def validate_parameter_ranges(
    angle_tolerance: Optional[float] = None,
    min_distance: Optional[float] = None,
    min_duration: Optional[float] = None,
    min_speed: Optional[float] = None,
    suspicious_angle_threshold: Optional[float] = None
) -> None:
    """
    Validate parameter ranges for segment detection.
    
    Args:
        angle_tolerance: Angle tolerance in degrees
        min_distance: Minimum distance in meters
        min_duration: Minimum duration in seconds
        min_speed: Minimum speed in knots
        suspicious_angle_threshold: Suspicious angle threshold in degrees
        
    Raises:
        ValidationError: If any parameter is out of valid range
    """
    if angle_tolerance is not None:
        if not 0 < angle_tolerance <= 180:
            raise ValidationError(f"Angle tolerance must be 0-180°, got {angle_tolerance}")
    
    if min_distance is not None:
        if not 0 <= min_distance <= 10000:  # 10km max
            raise ValidationError(f"Min distance must be 0-10000m, got {min_distance}")
    
    if min_duration is not None:
        if not 0 <= min_duration <= 3600:  # 1 hour max
            raise ValidationError(f"Min duration must be 0-3600s, got {min_duration}")
    
    if min_speed is not None:
        if not 0 <= min_speed <= 200:  # 200 knots max (very generous)
            raise ValidationError(f"Min speed must be 0-200 knots, got {min_speed}")
    
    if suspicious_angle_threshold is not None:
        if not 0 <= suspicious_angle_threshold <= 90:
            raise ValidationError(f"Suspicious angle threshold must be 0-90°, got {suspicious_angle_threshold}")


def validate_file_upload(uploaded_file: Any) -> None:
    """
    Validate uploaded file before processing.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Raises:
        ValidationError: If file validation fails
    """
    if uploaded_file is None:
        raise ValidationError("No file uploaded")
    
    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    if hasattr(uploaded_file, 'size') and uploaded_file.size > max_size:
        raise ValidationError(f"File too large: {uploaded_file.size / 1024 / 1024:.1f}MB (max 10MB)")
    
    # Check file extension
    if hasattr(uploaded_file, 'name'):
        file_path = Path(uploaded_file.name)
        if file_path.suffix.lower() != '.gpx':
            raise ValidationError(f"Invalid file type: {file_path.suffix} (expected .gpx)")
    
    logger.debug(f"File validation passed: {getattr(uploaded_file, 'name', 'unknown')}")


def safe_dataframe_operation(
    df: pd.DataFrame,
    operation: str,
    required_columns: Optional[List[str]] = None,
    min_rows: int = 0
) -> bool:
    """
    Check if a DataFrame operation can be safely performed.
    
    Args:
        df: DataFrame to check
        operation: Description of operation for error messages
        required_columns: Columns that must exist
        min_rows: Minimum number of rows required
        
    Returns:
        True if operation is safe, False otherwise
    """
    try:
        if df is None:
            logger.warning(f"Cannot perform {operation}: DataFrame is None")
            return False
        
        if df.empty and min_rows > 0:
            logger.warning(f"Cannot perform {operation}: DataFrame is empty")
            return False
        
        if len(df) < min_rows:
            logger.warning(f"Cannot perform {operation}: {len(df)} rows < {min_rows} required")
            return False
        
        if required_columns:
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                logger.warning(f"Cannot perform {operation}: Missing columns {missing}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking safety for {operation}: {e}")
        return False


def validate_and_clean_segments(segments: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean segments data, removing invalid entries.
    
    Args:
        segments: Raw segments DataFrame
        
    Returns:
        Cleaned segments DataFrame
    """
    if segments is None or segments.empty:
        return segments
    
    original_count = len(segments)
    cleaned = segments.copy()
    
    # Remove rows with NaN in critical columns
    critical_columns = ['distance', 'duration', 'bearing']
    available_critical = [col for col in critical_columns if col in cleaned.columns]
    
    if available_critical:
        cleaned = cleaned.dropna(subset=available_critical)
    
    # Remove impossible values
    if 'distance' in cleaned.columns:
        cleaned = cleaned[cleaned['distance'] >= 0]
    
    if 'duration' in cleaned.columns:
        cleaned = cleaned[cleaned['duration'] >= 0]
    
    if 'bearing' in cleaned.columns:
        cleaned = cleaned[cleaned['bearing'].between(0, 360)]
    
    if 'avg_speed_knots' in cleaned.columns:
        cleaned = cleaned[cleaned['avg_speed_knots'].between(0, 200)]  # Remove impossible speeds
    
    removed_count = original_count - len(cleaned)
    if removed_count > 0:
        logger.info(f"Cleaned segments: removed {removed_count} invalid entries")
    
    return cleaned