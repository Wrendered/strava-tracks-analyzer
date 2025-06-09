"""
Memory-based state management adapter.

This module provides implementations of state management interfaces
that work with in-memory storage, useful for testing and non-UI contexts.
"""

from typing import Any, Dict, List, Optional, TypeVar
import pandas as pd
import logging
from copy import deepcopy

from services.state import (
    StateService, WindStateService, SegmentStateService, 
    TrackStateService, FileWindSettingsService
)

logger = logging.getLogger(__name__)
T = TypeVar('T')


class MemoryStateAdapter(StateService[T]):
    """
    In-memory implementation of the StateService interface.
    
    This adapter provides state management using a simple dictionary,
    useful for testing, CLI applications, or other non-UI contexts.
    """
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
    
    def get(self, key: str, default: T = None) -> T:
        """Get value from memory state."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in memory state."""
        # Deep copy to avoid unintended mutations
        self._state[key] = deepcopy(value)
    
    def has(self, key: str) -> bool:
        """Check if key exists in memory state."""
        return key in self._state
    
    def delete(self, key: str) -> None:
        """Delete key from memory state."""
        if key in self._state:
            del self._state[key]
    
    def clear_all(self) -> None:
        """Clear all memory state."""
        self._state.clear()
    
    def update_if_changed(self, key: str, new_value: Any) -> bool:
        """Update memory state only if value has changed."""
        prev_value = self._state.get(key)
        if prev_value is None or prev_value != new_value:
            self._state[key] = deepcopy(new_value)
            return True
        return False
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get a copy of all state (useful for debugging/testing)."""
        return deepcopy(self._state)
    
    def load_state(self, state: Dict[str, Any]) -> None:
        """Load state from dictionary (useful for testing)."""
        self._state = deepcopy(state)


class MemoryWindStateAdapter(WindStateService):
    """
    Memory implementation of wind state management.
    """
    
    def __init__(self, state_service: StateService):
        self._state = state_service
    
    def get_wind_direction(self, default: Optional[float] = None) -> float:
        """Get current wind direction from memory state."""
        if default is None:
            from config.settings import DEFAULT_WIND_DIRECTION
            default = DEFAULT_WIND_DIRECTION
        
        return self._state.get('wind_direction', default)
    
    def set_wind_direction(self, direction: float) -> None:
        """Set wind direction in memory state with normalization."""
        # Normalize the angle to 0-359 range
        normalized = direction % 360
        self._state.set('wind_direction', normalized)
    
    def get_estimated_wind(self) -> Optional[float]:
        """Get estimated wind direction from memory state."""
        return self._state.get('estimated_wind')
    
    def set_estimated_wind(self, direction: float) -> None:
        """Set estimated wind direction in memory state with normalization."""
        normalized = direction % 360
        self._state.set('estimated_wind', normalized)


class MemorySegmentStateAdapter(SegmentStateService):
    """
    Memory implementation of segment state management.
    """
    
    def __init__(self, state_service: StateService):
        self._state = state_service
    
    def get_track_data(self) -> Optional[pd.DataFrame]:
        """Get current track data from memory state."""
        return self._state.get('track_data')
    
    def set_track_data(self, data: pd.DataFrame) -> None:
        """Set track data in memory state."""
        self._state.set('track_data', data)
    
    def get_track_stretches(self) -> Optional[pd.DataFrame]:
        """Get current track stretches from memory state."""
        return self._state.get('track_stretches')
    
    def set_track_stretches(self, stretches: pd.DataFrame) -> None:
        """Set track stretches in memory state."""
        self._state.set('track_stretches', stretches)
    
    def get_selected_segments(self) -> List[int]:
        """Get list of selected segment indices from memory state."""
        selected = self._state.get('selected_segments', [])
        return selected if selected is not None else []
    
    def set_selected_segments(self, segment_indices: List[int]) -> None:
        """Set selected segment indices in memory state."""
        self._state.set('selected_segments', segment_indices)
    
    def get_segment_parameters(self) -> Dict[str, Any]:
        """Get all segment detection parameters from memory state."""
        from config.settings import (
            DEFAULT_ANGLE_TOLERANCE,
            DEFAULT_MIN_DURATION,
            DEFAULT_MIN_DISTANCE,
            DEFAULT_MIN_SPEED,
            DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
        )
        
        return {
            'angle_tolerance': self._state.get('angle_tolerance', DEFAULT_ANGLE_TOLERANCE),
            'min_duration': self._state.get('min_duration', DEFAULT_MIN_DURATION),
            'min_distance': self._state.get('min_distance', DEFAULT_MIN_DISTANCE),
            'min_speed': self._state.get('min_speed', DEFAULT_MIN_SPEED),
            'suspicious_angle_threshold': self._state.get('suspicious_angle_threshold', 
                                                          DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD),
        }


class MemoryTrackStateAdapter(TrackStateService):
    """
    Memory implementation of track metadata state management.
    """
    
    def __init__(self, state_service: StateService):
        self._state = state_service
    
    def get_track_name(self) -> Optional[str]:
        """Get current track name from memory state."""
        return self._state.get('track_name')
    
    def set_track_name(self, name: str) -> None:
        """Set track name in memory state."""
        self._state.set('track_name', name)
    
    def get_track_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current track metrics from memory state."""
        return self._state.get('track_metrics')
    
    def set_track_metrics(self, metrics: Dict[str, Any]) -> None:
        """Set track metrics in memory state."""
        self._state.set('track_metrics', metrics)
    
    def get_current_file_name(self) -> Optional[str]:
        """Get current file name from memory state."""
        return self._state.get('current_file_name')
    
    def set_current_file_name(self, file_name: str) -> None:
        """Set current file name in memory state."""
        self._state.set('current_file_name', file_name)


class MemoryFileWindSettingsAdapter(FileWindSettingsService):
    """
    Memory implementation of file-specific wind settings state management.
    """
    
    def __init__(self, state_service: StateService):
        self._state = state_service
        self._ensure_initialized()
    
    def _ensure_initialized(self) -> None:
        """Ensure file wind settings dictionary exists in memory state."""
        if not self._state.has('file_wind_settings'):
            self._state.set('file_wind_settings', {})
    
    def get_wind_settings(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Get wind settings for a specific file."""
        self._ensure_initialized()
        file_settings = self._state.get('file_wind_settings', {})
        return file_settings.get(file_name)
    
    def set_wind_settings(self, file_name: str, settings: Dict[str, Any]) -> None:
        """Set wind settings for a specific file."""
        self._ensure_initialized()
        file_settings = self._state.get('file_wind_settings', {})
        file_settings[file_name] = settings
        self._state.set('file_wind_settings', file_settings)
    
    def update_wind_direction(self, file_name: str, direction: float) -> None:
        """Update wind direction for a specific file."""
        self._ensure_initialized()
        file_settings = self._state.get('file_wind_settings', {})
        if file_name not in file_settings:
            file_settings[file_name] = {}
        file_settings[file_name]['wind_direction'] = direction
        self._state.set('file_wind_settings', file_settings)


def create_memory_adapters() -> Dict[str, Any]:
    """
    Create all memory state adapters.
    
    Returns:
        Dictionary with all adapter instances
    """
    # Create the base state adapter
    state_adapter = MemoryStateAdapter()
    
    # Create specialized adapters that use the base adapter
    wind_adapter = MemoryWindStateAdapter(state_adapter)
    segment_adapter = MemorySegmentStateAdapter(state_adapter)
    track_adapter = MemoryTrackStateAdapter(state_adapter)
    file_wind_adapter = MemoryFileWindSettingsAdapter(state_adapter)
    
    return {
        'state': state_adapter,
        'wind': wind_adapter,
        'segment': segment_adapter,
        'track': track_adapter,
        'file_wind': file_wind_adapter
    }


def register_memory_adapters() -> None:
    """
    Register all memory adapters with the StateServiceRegistry.
    
    This function should be called once at application startup
    to configure dependency injection for memory-based contexts.
    """
    from services.state import StateServiceRegistry
    
    adapters = create_memory_adapters()
    
    StateServiceRegistry.register_state_service(adapters['state'])
    StateServiceRegistry.register_wind_service(adapters['wind'])
    StateServiceRegistry.register_segment_service(adapters['segment'])
    StateServiceRegistry.register_track_service(adapters['track'])
    StateServiceRegistry.register_file_wind_service(adapters['file_wind'])
    
    logger.info("Memory state adapters registered successfully")