"""
Abstract state management interfaces and framework adapters.

This module provides framework-agnostic state management abstractions,
enabling clean separation between business logic and UI framework dependencies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
import pandas as pd
from datetime import datetime

T = TypeVar('T')


class StateService(ABC, Generic[T]):
    """
    Abstract interface for state management services.
    
    This interface defines the contract that all state management
    implementations must follow, enabling dependency injection and
    framework independence.
    """
    
    @abstractmethod
    def get(self, key: str, default: T = None) -> T:
        """
        Get a value from state.
        
        Args:
            key: State key to retrieve
            default: Default value if key not found
            
        Returns:
            Value from state or default
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in state.
        
        Args:
            key: State key to set
            value: Value to store
        """
        pass
    
    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check if key exists in state.
        
        Args:
            key: State key to check
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete a key from state.
        
        Args:
            key: State key to delete
        """
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        """Clear all state values."""
        pass
    
    @abstractmethod
    def update_if_changed(self, key: str, new_value: Any) -> bool:
        """
        Update state only if value has changed.
        
        Args:
            key: State key to update
            new_value: New value to set
            
        Returns:
            True if value was updated, False if unchanged
        """
        pass


class WindStateService(ABC):
    """Abstract interface for wind-related state management."""
    
    @abstractmethod
    def get_wind_direction(self, default: Optional[float] = None) -> float:
        """Get current wind direction from state."""
        pass
    
    @abstractmethod
    def set_wind_direction(self, direction: float) -> None:
        """Set wind direction in state."""
        pass
    
    @abstractmethod
    def get_estimated_wind(self) -> Optional[float]:
        """Get estimated wind direction from state."""
        pass
    
    @abstractmethod
    def set_estimated_wind(self, direction: float) -> None:
        """Set estimated wind direction in state."""
        pass


class SegmentStateService(ABC):
    """Abstract interface for segment-related state management."""
    
    @abstractmethod
    def get_track_data(self) -> Optional[pd.DataFrame]:
        """Get track data from state."""
        pass
    
    @abstractmethod
    def set_track_data(self, data: pd.DataFrame) -> None:
        """Set track data in state."""
        pass
    
    @abstractmethod
    def get_track_stretches(self) -> Optional[pd.DataFrame]:
        """Get track stretches from state."""
        pass
    
    @abstractmethod
    def set_track_stretches(self, stretches: pd.DataFrame) -> None:
        """Set track stretches in state."""
        pass
    
    @abstractmethod
    def get_selected_segments(self) -> List[int]:
        """Get selected segment indices from state."""
        pass
    
    @abstractmethod
    def set_selected_segments(self, segment_indices: List[int]) -> None:
        """Set selected segment indices in state."""
        pass
    
    @abstractmethod
    def get_segment_parameters(self) -> Dict[str, Any]:
        """Get all segment detection parameters from state."""
        pass


class TrackStateService(ABC):
    """Abstract interface for track metadata state management."""
    
    @abstractmethod
    def get_track_name(self) -> Optional[str]:
        """Get track name from state."""
        pass
    
    @abstractmethod
    def set_track_name(self, name: str) -> None:
        """Set track name in state."""
        pass
    
    @abstractmethod
    def get_track_metrics(self) -> Optional[Dict[str, Any]]:
        """Get track metrics from state."""
        pass
    
    @abstractmethod
    def set_track_metrics(self, metrics: Dict[str, Any]) -> None:
        """Set track metrics in state."""
        pass
    
    @abstractmethod
    def get_current_file_name(self) -> Optional[str]:
        """Get current file name from state."""
        pass
    
    @abstractmethod
    def set_current_file_name(self, file_name: str) -> None:
        """Set current file name in state."""
        pass


class FileWindSettingsService(ABC):
    """Abstract interface for file-specific wind settings state management."""
    
    @abstractmethod
    def get_wind_settings(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Get wind settings for a specific file."""
        pass
    
    @abstractmethod
    def set_wind_settings(self, file_name: str, settings: Dict[str, Any]) -> None:
        """Set wind settings for a specific file."""
        pass
    
    @abstractmethod
    def update_wind_direction(self, file_name: str, direction: float) -> None:
        """Update wind direction for a specific file."""
        pass


class StateServiceRegistry:
    """
    Registry for state service implementations.
    
    This class manages dependency injection for state services,
    allowing different implementations to be used based on context
    (e.g., Streamlit, Flask, testing, etc.).
    """
    
    _state_service: Optional[StateService] = None
    _wind_service: Optional[WindStateService] = None
    _segment_service: Optional[SegmentStateService] = None
    _track_service: Optional[TrackStateService] = None
    _file_wind_service: Optional[FileWindSettingsService] = None
    
    @classmethod
    def register_state_service(cls, service: StateService) -> None:
        """Register the primary state service implementation."""
        cls._state_service = service
    
    @classmethod
    def register_wind_service(cls, service: WindStateService) -> None:
        """Register the wind state service implementation."""
        cls._wind_service = service
    
    @classmethod
    def register_segment_service(cls, service: SegmentStateService) -> None:
        """Register the segment state service implementation."""
        cls._segment_service = service
    
    @classmethod
    def register_track_service(cls, service: TrackStateService) -> None:
        """Register the track state service implementation."""
        cls._track_service = service
    
    @classmethod
    def register_file_wind_service(cls, service: FileWindSettingsService) -> None:
        """Register the file wind settings service implementation."""
        cls._file_wind_service = service
    
    @classmethod
    def get_state_service(cls) -> StateService:
        """Get the registered state service."""
        if cls._state_service is None:
            raise RuntimeError("No state service registered. Call register_state_service() first.")
        return cls._state_service
    
    @classmethod
    def get_wind_service(cls) -> WindStateService:
        """Get the registered wind state service."""
        if cls._wind_service is None:
            raise RuntimeError("No wind service registered. Call register_wind_service() first.")
        return cls._wind_service
    
    @classmethod
    def get_segment_service(cls) -> SegmentStateService:
        """Get the registered segment state service."""
        if cls._segment_service is None:
            raise RuntimeError("No segment service registered. Call register_segment_service() first.")
        return cls._segment_service
    
    @classmethod
    def get_track_service(cls) -> TrackStateService:
        """Get the registered track state service."""
        if cls._track_service is None:
            raise RuntimeError("No track service registered. Call register_track_service() first.")
        return cls._track_service
    
    @classmethod
    def get_file_wind_service(cls) -> FileWindSettingsService:
        """Get the registered file wind settings service."""
        if cls._file_wind_service is None:
            raise RuntimeError("No file wind service registered. Call register_file_wind_service() first.")
        return cls._file_wind_service
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all registered services."""
        cls._state_service = None
        cls._wind_service = None
        cls._segment_service = None
        cls._track_service = None
        cls._file_wind_service = None


# Dependency injection decorators
def inject_state_service(func):
    """Decorator to inject state service into function."""
    def wrapper(*args, **kwargs):
        state_service = StateServiceRegistry.get_state_service()
        return func(state_service, *args, **kwargs)
    return wrapper


def inject_wind_service(func):
    """Decorator to inject wind state service into function."""
    def wrapper(*args, **kwargs):
        wind_service = StateServiceRegistry.get_wind_service()
        return func(wind_service, *args, **kwargs)
    return wrapper


def inject_segment_service(func):
    """Decorator to inject segment state service into function."""
    def wrapper(*args, **kwargs):
        segment_service = StateServiceRegistry.get_segment_service()
        return func(segment_service, *args, **kwargs)
    return wrapper