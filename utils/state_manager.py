"""
State management utilities for Streamlit applications.

This module provides centralized state management functionality,
abstracting away the details of Streamlit's session_state.
"""

import streamlit as st
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, cast
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from copy import deepcopy

logger = logging.getLogger(__name__)

T = TypeVar('T')

class StateManager:
    """
    Centralized manager for Streamlit session state.
    
    This class provides a consistent interface for working with Streamlit's
    session state, including type hints, default values, and change tracking.
    """
    
    @staticmethod
    def get(key: str, default_value: T = None) -> T:
        """
        Get a value from session state with a default if not present.
        
        Args:
            key: The key to retrieve from session state
            default_value: Default value to return if key is not in session state
            
        Returns:
            The value from session state, or the default value
        """
        return st.session_state.get(key, default_value)
    
    @staticmethod
    def set(key: str, value: Any) -> None:
        """
        Set a value in session state.
        
        Args:
            key: The key to set in session state
            value: The value to store
        """
        st.session_state[key] = value
        
    @staticmethod
    def has(key: str) -> bool:
        """
        Check if a key exists in session state.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        return key in st.session_state
    
    @staticmethod
    def delete(key: str) -> None:
        """
        Delete a key from session state if it exists.
        
        Args:
            key: The key to delete
        """
        if key in st.session_state:
            del st.session_state[key]
            
    @staticmethod
    def clear_all() -> None:
        """Clear all session state values."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    @staticmethod
    def track_change(key: str, new_value: Any) -> bool:
        """
        Track if a value has changed by comparing with session state.
        
        Args:
            key: The key to check for changes
            new_value: The new value to compare against session state
            
        Returns:
            True if the value has changed or is not in session state
        """
        prev_value = st.session_state.get(key)
        if prev_value is None or prev_value != new_value:
            return True
        return False
    
    @staticmethod
    def update_if_changed(key: str, new_value: Any) -> bool:
        """
        Update session state only if the value has changed.
        
        Args:
            key: The key to potentially update
            new_value: The new value to set if different from current
            
        Returns:
            True if the value was updated, False if unchanged
        """
        changed = StateManager.track_change(key, new_value)
        if changed:
            st.session_state[key] = new_value
        return changed


# Wind analysis specific state management
class WindStateManager:
    """
    Specialized state manager for wind analysis related state.
    
    Provides typed access to wind-specific state values with appropriate
    defaults from configuration.
    """
    
    @staticmethod
    def get_wind_direction(default: float = None) -> float:
        """
        Get the current wind direction from session state.
        
        Args:
            default: Default wind direction if not in session state
            
        Returns:
            Current wind direction in degrees (0-359)
        """
        if default is None:
            from config.settings import DEFAULT_WIND_DIRECTION
            default = DEFAULT_WIND_DIRECTION
            
        return StateManager.get('wind_direction', default)
    
    @staticmethod
    def set_wind_direction(direction: float) -> None:
        """
        Set the wind direction in session state.
        
        Args:
            direction: Wind direction in degrees (0-359)
        """
        # Normalize the angle to 0-359 range
        normalized = direction % 360
        StateManager.set('wind_direction', normalized)
    
    @staticmethod
    def get_estimated_wind() -> Optional[float]:
        """
        Get the estimated wind direction from session state.
        
        Returns:
            Estimated wind direction or None if not available
        """
        return StateManager.get('estimated_wind')
    
    @staticmethod
    def set_estimated_wind(direction: float) -> None:
        """
        Set the estimated wind direction in session state.
        
        Args:
            direction: Estimated wind direction in degrees (0-359)
        """
        normalized = direction % 360
        StateManager.set('estimated_wind', normalized)


# Segment analysis specific state management
class SegmentStateManager:
    """
    Specialized state manager for segment analysis related state.
    
    Provides typed access to segment-specific state values with appropriate
    defaults from configuration.
    """
    
    @staticmethod
    def get_track_data() -> Optional[pd.DataFrame]:
        """
        Get the current track data from session state.
        
        Returns:
            DataFrame with track data or None if not loaded
        """
        return StateManager.get('track_data')
    
    @staticmethod
    def set_track_data(data: pd.DataFrame) -> None:
        """
        Set the track data in session state.
        
        Args:
            data: DataFrame with track data
        """
        StateManager.set('track_data', data)
    
    @staticmethod
    def get_track_stretches() -> Optional[pd.DataFrame]:
        """
        Get the current track stretches from session state.
        
        Returns:
            DataFrame with track stretches or None if not calculated
        """
        return StateManager.get('track_stretches')
    
    @staticmethod
    def set_track_stretches(stretches: pd.DataFrame) -> None:
        """
        Set the track stretches in session state.
        
        Args:
            stretches: DataFrame with track stretches
        """
        StateManager.set('track_stretches', stretches)
    
    @staticmethod
    def get_selected_segments() -> List[int]:
        """
        Get the list of selected segment indices from session state.
        
        Returns:
            List of selected segment indices or empty list if none selected
        """
        selected = StateManager.get('selected_segments', [])
        return selected if selected is not None else []
    
    @staticmethod
    def set_selected_segments(segment_indices: List[int]) -> None:
        """
        Set the selected segment indices in session state.
        
        Args:
            segment_indices: List of selected segment indices
        """
        StateManager.set('selected_segments', segment_indices)
        
    @staticmethod
    def get_segment_parameters() -> Dict[str, Any]:
        """
        Get all segment detection parameters from session state.
        
        Returns:
            Dictionary with all segment parameters and their current values
        """
        from config.settings import (
            DEFAULT_ANGLE_TOLERANCE,
            DEFAULT_MIN_DURATION,
            DEFAULT_MIN_DISTANCE,
            DEFAULT_MIN_SPEED,
            DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
        )
        
        return {
            'angle_tolerance': StateManager.get('angle_tolerance', DEFAULT_ANGLE_TOLERANCE),
            'min_duration': StateManager.get('min_duration', DEFAULT_MIN_DURATION),
            'min_distance': StateManager.get('min_distance', DEFAULT_MIN_DISTANCE),
            'min_speed': StateManager.get('min_speed', DEFAULT_MIN_SPEED),
            'suspicious_angle_threshold': StateManager.get('suspicious_angle_threshold', 
                                                          DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD),
        }


# Track metadata state management
class TrackStateManager:
    """
    Specialized state manager for track metadata.
    
    Provides typed access to track-specific state values.
    """
    
    @staticmethod
    def get_track_name() -> Optional[str]:
        """
        Get the current track name from session state.
        
        Returns:
            Track name or None if not available
        """
        return StateManager.get('track_name')
    
    @staticmethod
    def set_track_name(name: str) -> None:
        """
        Set the track name in session state.
        
        Args:
            name: Track name
        """
        StateManager.set('track_name', name)
    
    @staticmethod
    def get_track_metrics() -> Optional[Dict[str, Any]]:
        """
        Get the current track metrics from session state.
        
        Returns:
            Dictionary with track metrics or None if not calculated
        """
        return StateManager.get('track_metrics')
    
    @staticmethod
    def set_track_metrics(metrics: Dict[str, Any]) -> None:
        """
        Set the track metrics in session state.
        
        Args:
            metrics: Dictionary with track metrics
        """
        StateManager.set('track_metrics', metrics)
    
    @staticmethod
    def get_current_file_name() -> Optional[str]:
        """
        Get the current file name from session state.
        
        Returns:
            Current file name or None if not available
        """
        return StateManager.get('current_file_name')
    
    @staticmethod
    def set_current_file_name(file_name: str) -> None:
        """
        Set the current file name in session state.
        
        Args:
            file_name: Current file name
        """
        StateManager.set('current_file_name', file_name)


# File wind settings state management
class FileWindSettingsManager:
    """
    Specialized state manager for file-specific wind settings.
    
    Provides typed access to file wind settings with persistence.
    """
    
    @staticmethod
    def _ensure_initialized() -> None:
        """Ensure file wind settings dictionary exists in session state."""
        if 'file_wind_settings' not in st.session_state:
            st.session_state.file_wind_settings = {}
    
    @staticmethod
    def get_wind_settings(file_name: str) -> Optional[Dict[str, Any]]:
        """
        Get wind settings for a specific file.
        
        Args:
            file_name: The file to get settings for
            
        Returns:
            Dictionary with wind settings or None if not available
        """
        FileWindSettingsManager._ensure_initialized()
        return st.session_state.file_wind_settings.get(file_name)
    
    @staticmethod
    def set_wind_settings(file_name: str, settings: Dict[str, Any]) -> None:
        """
        Set wind settings for a specific file.
        
        Args:
            file_name: The file to set settings for
            settings: Dictionary with wind settings
        """
        FileWindSettingsManager._ensure_initialized()
        st.session_state.file_wind_settings[file_name] = settings
    
    @staticmethod
    def update_wind_direction(file_name: str, direction: float) -> None:
        """
        Update wind direction for a specific file.
        
        Args:
            file_name: The file to update
            direction: New wind direction
        """
        FileWindSettingsManager._ensure_initialized()
        if file_name not in st.session_state.file_wind_settings:
            st.session_state.file_wind_settings[file_name] = {}
        st.session_state.file_wind_settings[file_name]['wind_direction'] = direction