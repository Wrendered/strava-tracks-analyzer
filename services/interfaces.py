"""
Service interfaces and abstract base classes.

This module defines the contracts that services should implement,
promoting consistency and enabling easier testing and mocking.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from core.wind.models import WindEstimate


class TrackAnalysisService(ABC):
    """Abstract interface for track analysis services."""
    
    @abstractmethod
    def analyze_track_file(
        self,
        file,
        initial_wind_direction: float,
        **kwargs
    ) -> Any:
        """
        Analyze a track file and return analysis results.
        
        Args:
            file: File object or path to analyze
            initial_wind_direction: Initial wind direction estimate
            **kwargs: Additional analysis parameters
            
        Returns:
            Analysis result object
        """
        pass
    
    @abstractmethod
    def analyze_track_data(
        self,
        track_data: pd.DataFrame,
        initial_wind_direction: float,
        **kwargs
    ) -> Any:
        """
        Analyze track data in memory.
        
        Args:
            track_data: DataFrame with track data
            initial_wind_direction: Initial wind direction estimate
            **kwargs: Additional analysis parameters
            
        Returns:
            Analysis result object
        """
        pass


class WindAnalysisService(ABC):
    """Abstract interface for wind analysis services."""
    
    @abstractmethod
    def estimate_wind_direction(
        self,
        segments: pd.DataFrame,
        initial_wind: float,
        **kwargs
    ) -> WindEstimate:
        """
        Estimate wind direction from sailing segments.
        
        Args:
            segments: DataFrame with sailing segments
            initial_wind: Initial wind direction estimate
            **kwargs: Additional estimation parameters
            
        Returns:
            WindEstimate with direction and confidence
        """
        pass
    
    @abstractmethod
    def update_segments_with_wind(
        self,
        segments: pd.DataFrame,
        wind_direction: float
    ) -> pd.DataFrame:
        """
        Update segments with wind direction analysis.
        
        Args:
            segments: DataFrame with segments
            wind_direction: Wind direction in degrees
            
        Returns:
            Updated DataFrame with wind analysis
        """
        pass
    
    @abstractmethod
    def analyze_wind_performance(
        self,
        segments: pd.DataFrame,
        wind_direction: float
    ) -> Dict[str, Any]:
        """
        Analyze wind performance metrics.
        
        Args:
            segments: DataFrame with wind-analyzed segments
            wind_direction: Wind direction used for analysis
            
        Returns:
            Dictionary with performance metrics
        """
        pass


class SegmentAnalysisService(ABC):
    """Abstract interface for segment analysis services."""
    
    @abstractmethod
    def detect_segments(
        self,
        track_data: pd.DataFrame,
        **kwargs
    ) -> pd.DataFrame:
        """
        Detect consistent segments in track data.
        
        Args:
            track_data: DataFrame with GPS track data
            **kwargs: Detection parameters
            
        Returns:
            DataFrame with detected segments
        """
        pass
    
    @abstractmethod
    def analyze_segments_with_wind(
        self,
        segments: pd.DataFrame,
        wind_direction: float,
        **kwargs
    ) -> pd.DataFrame:
        """
        Analyze segments with wind direction.
        
        Args:
            segments: DataFrame with segments
            wind_direction: Wind direction in degrees
            **kwargs: Analysis parameters
            
        Returns:
            DataFrame with wind analysis added
        """
        pass
    
    @abstractmethod
    def get_segment_summary(
        self,
        segments: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Get summary statistics for segments.
        
        Args:
            segments: DataFrame with segments
            
        Returns:
            Dictionary with summary statistics
        """
        pass


class DataTransformationService(ABC):
    """Abstract interface for data transformation services."""
    
    @abstractmethod
    def transform_gpx_to_dataframe(
        self,
        gpx_data: Any
    ) -> pd.DataFrame:
        """
        Transform GPX data to DataFrame format.
        
        Args:
            gpx_data: GPX data object
            
        Returns:
            DataFrame with track data
        """
        pass
    
    @abstractmethod
    def validate_track_data(
        self,
        track_data: pd.DataFrame
    ) -> bool:
        """
        Validate track data format and content.
        
        Args:
            track_data: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass


class MetricsCalculationService(ABC):
    """Abstract interface for metrics calculation services."""
    
    @abstractmethod
    def calculate_vmg(
        self,
        segments: pd.DataFrame,
        **kwargs
    ) -> float:
        """
        Calculate Velocity Made Good.
        
        Args:
            segments: DataFrame with segments
            **kwargs: Calculation parameters
            
        Returns:
            VMG value
        """
        pass
    
    @abstractmethod
    def calculate_performance_metrics(
        self,
        segments: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            segments: DataFrame with segments
            
        Returns:
            Dictionary with performance metrics
        """
        pass


class StateManagementService(ABC):
    """Abstract interface for state management services."""
    
    @abstractmethod
    def get_state(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get value from state.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            State value
        """
        pass
    
    @abstractmethod
    def set_state(
        self,
        key: str,
        value: Any
    ) -> None:
        """
        Set value in state.
        
        Args:
            key: State key
            value: Value to set
        """
        pass
    
    @abstractmethod
    def update_state(
        self,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update multiple state values.
        
        Args:
            updates: Dictionary of key-value pairs to update
        """
        pass


# Service registry for dependency injection
class ServiceRegistry:
    """Registry for service implementations."""
    
    _services: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, interface: type, implementation: Any) -> None:
        """
        Register a service implementation.
        
        Args:
            interface: Service interface class
            implementation: Service implementation instance
        """
        cls._services[interface.__name__] = implementation
    
    @classmethod
    def get(cls, interface: type) -> Any:
        """
        Get a service implementation.
        
        Args:
            interface: Service interface class
            
        Returns:
            Service implementation instance
            
        Raises:
            KeyError: If service not registered
        """
        service_name = interface.__name__
        if service_name not in cls._services:
            raise KeyError(f"No implementation registered for {service_name}")
        return cls._services[service_name]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered services."""
        cls._services.clear()


# Dependency injection decorator
def inject_service(interface: type):
    """
    Decorator to inject service dependencies.
    
    Args:
        interface: Service interface to inject
        
    Returns:
        Decorated function with injected service
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            service = ServiceRegistry.get(interface)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator