"""
UI callback handlers for Streamlit components.

This module provides centralized callback functions for UI components,
separating event handling from business logic and UI rendering.
"""

import streamlit as st
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from services.segment_service import SegmentService
from services.wind_service import WindService
from utils.state_manager import StateManager, SegmentStateManager, WindStateManager, TrackStateManager

logger = logging.getLogger(__name__)

# Wind Direction Callbacks

def on_wind_direction_change(new_wind_direction: float) -> bool:
    """
    Callback for wind direction changes.
    
    Args:
        new_wind_direction: The new wind direction to set
        
    Returns:
        bool: True if update was successful and should trigger rerun
    """
    # Update current file's settings
    current_file = TrackStateManager.get_current_file_name()
    
    # Use the wind service to update wind direction
    if WindService.update_wind_direction(new_wind_direction):
        # Update this file's settings in our persistent dictionary
        if current_file:
            from utils.state_manager import FileWindSettingsManager
            FileWindSettingsManager.update_wind_direction(current_file, new_wind_direction)
        
        logger.info(f"Wind direction successfully updated to {new_wind_direction}°")
        return True
    
    logger.error(f"Failed to update wind direction to {new_wind_direction}°")
    return False

def on_wind_reestimation(segments: pd.DataFrame, current_wind: float, suspicious_angle_threshold: float) -> bool:
    """
    Callback for wind direction re-estimation.
    
    Args:
        segments: DataFrame with segments to analyze
        current_wind: Current wind direction
        suspicious_angle_threshold: Threshold for suspicious angles
        
    Returns:
        bool: True if estimation and update was successful
    """
    # Use the wind service to estimate wind direction
    wind_estimate = WindService.estimate_wind_direction(
        segments,
        method="weighted",
    )
    
    # If estimation was successful
    if not wind_estimate.user_provided:
        refined_wind = wind_estimate.direction
        
        # Store the estimate for reference
        WindStateManager.set_estimated_wind(refined_wind)
        StateManager.set('wind_estimate', wind_estimate.to_dict())
        
        # Update the wind direction
        return WindService.update_wind_direction(refined_wind)
    
    return False

# Segment Parameter Callbacks

def on_segment_parameter_change() -> bool:
    """
    Callback for segment parameter changes.
    
    Returns:
        bool: True if recalculation was successful and should trigger rerun
    """
    # Only recalculate if we have data
    if SegmentStateManager.get_track_data() is not None:
        return SegmentService.recalculate_segments("segment parameters")
    return False

def on_angle_tolerance_change(angle_tolerance: float) -> bool:
    """
    Callback for angle tolerance parameter changes.
    
    Args:
        angle_tolerance: New angle tolerance value
        
    Returns:
        bool: True if parameter was changed and recalculation succeeded
    """
    # Check if the value actually changed
    if StateManager.update_if_changed('angle_tolerance', angle_tolerance):
        return on_segment_parameter_change()
    return False

def on_min_duration_change(min_duration: float) -> bool:
    """
    Callback for minimum duration parameter changes.
    
    Args:
        min_duration: New minimum duration value
        
    Returns:
        bool: True if parameter was changed and recalculation succeeded
    """
    # Check if the value actually changed
    if StateManager.update_if_changed('min_duration', min_duration):
        return on_segment_parameter_change()
    return False

def on_min_distance_change(min_distance: float) -> bool:
    """
    Callback for minimum distance parameter changes.
    
    Args:
        min_distance: New minimum distance value
        
    Returns:
        bool: True if parameter was changed and recalculation succeeded
    """
    # Check if the value actually changed
    if StateManager.update_if_changed('min_distance', min_distance):
        return on_segment_parameter_change()
    return False

def on_min_speed_change(min_speed: float) -> bool:
    """
    Callback for minimum speed parameter changes.
    
    Args:
        min_speed: New minimum speed value
        
    Returns:
        bool: True if parameter was changed and recalculation succeeded
    """
    # Check if the value actually changed
    if StateManager.update_if_changed('min_speed', min_speed):
        return on_segment_parameter_change()
    return False

def on_suspicious_angle_threshold_change(threshold: float) -> bool:
    """
    Callback for suspicious angle threshold parameter changes.
    
    Args:
        threshold: New suspicious angle threshold value
        
    Returns:
        bool: True if parameter was changed and recalculation succeeded
    """
    # Check if the value actually changed
    if StateManager.update_if_changed('suspicious_angle_threshold', threshold):
        return on_segment_parameter_change()
    return False

def on_active_speed_threshold_change(threshold: float) -> bool:
    """
    Callback for active speed threshold parameter changes.
    
    Args:
        threshold: New active speed threshold value
        
    Returns:
        bool: True if parameter was changed (no recalculation needed)
    """
    # This parameter doesn't trigger segment recalculation, just store it
    return StateManager.update_if_changed('active_speed_threshold', threshold)

# Track Data Callbacks

def on_clear_track_data() -> bool:
    """
    Callback for clearing track data.
    
    Returns:
        bool: True to trigger rerun
    """
    # Clear all track-related state
    TrackStateManager.set_track_data(None)
    TrackStateManager.set_track_metrics(None)
    SegmentStateManager.set_track_stretches(None)
    TrackStateManager.set_track_name(None)
    WindStateManager.set_wind_direction(None)  # Will use default
    WindStateManager.set_estimated_wind(None)
    TrackStateManager.set_current_file_name(None)
    StateManager.set('analyze_confirmed', False)
    
    return True  # Always rerun

def on_analyze_track_confirmed(file_name: str) -> bool:
    """
    Callback for confirming track analysis.
    
    Args:
        file_name: Name of the file to analyze
        
    Returns:
        bool: True to mark as confirmed
    """
    StateManager.set('analyze_confirmed', True)
    StateManager.set('process_this_file', file_name)
    return True

# Segment Selection Callbacks

def on_segment_selection_change(selected_segments: List[int]) -> bool:
    """
    Callback for segment selection changes.
    
    Args:
        selected_segments: List of selected segment indices
        
    Returns:
        bool: True if selection was changed
    """
    return StateManager.update_if_changed('selected_segments', selected_segments)