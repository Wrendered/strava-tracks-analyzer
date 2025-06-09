"""
Pure wind analysis service with no state dependencies.

This module provides clean business logic for wind direction estimation
without coupling to UI frameworks or state management systems.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass

from core.wind.factory import estimate_wind_direction_factory, WindEstimationParams
from core.wind.models import WindEstimate
from core.calculations import analyze_wind_angles


logger = logging.getLogger(__name__)


@dataclass
class WindAnalysisParams:
    """Parameters for wind analysis operations."""
    initial_wind_direction: float
    suspicious_angle_threshold: float = 20.0
    min_segment_distance: float = 50.0
    max_iterations: int = 5
    estimation_method: str = "iterative"


@dataclass
class WindAnalysisResult:
    """Result of wind analysis operations."""
    wind_estimate: WindEstimate
    updated_segments: pd.DataFrame
    success: bool
    error_message: Optional[str] = None


class PureWindAnalysisService:
    """
    Pure wind analysis service with no external dependencies.
    
    This service provides clean business logic for wind analysis operations
    without any coupling to UI frameworks or state management systems.
    All data is passed explicitly as parameters.
    """
    
    @staticmethod
    def estimate_wind_direction(
        segments: pd.DataFrame,
        params: WindAnalysisParams
    ) -> WindEstimate:
        """
        Estimate wind direction from sailing segments.
        
        Args:
            segments: DataFrame with sailing segments
            params: Parameters for wind estimation
            
        Returns:
            WindEstimate with direction and confidence
        """
        if segments.empty:
            logger.warning("No segments provided for wind estimation")
            return WindEstimate(
                direction=params.initial_wind_direction,
                confidence="None",
                port_average_angle=0,
                starboard_average_angle=0,
                total_segments=0,
                port_segments=0,
                starboard_segments=0
            )
        
        logger.info(f"Estimating wind direction from {len(segments)} segments")
        logger.info(f"Initial wind direction: {params.initial_wind_direction}°")
        
        try:
            # Create wind estimation parameters
            wind_params = WindEstimationParams(
                suspicious_angle_threshold=params.suspicious_angle_threshold,
                min_segment_distance=params.min_segment_distance,
                max_iterations=params.max_iterations
            )
            
            # Use factory pattern for wind estimation
            result = estimate_wind_direction_factory(
                segments.copy(),
                initial_wind=params.initial_wind_direction,
                method=params.estimation_method,
                params=wind_params
            )
            
            logger.info(f"Estimated wind direction: {result.direction:.1f}° "
                       f"(confidence: {result.confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Wind estimation failed: {e}")
            return WindEstimate(
                direction=params.initial_wind_direction,
                confidence="None",
                port_average_angle=0,
                starboard_average_angle=0,
                total_segments=len(segments),
                port_segments=0,
                starboard_segments=0
            )
    
    @staticmethod
    def update_segments_with_wind(
        segments: pd.DataFrame,
        wind_direction: float
    ) -> pd.DataFrame:
        """
        Update segments with new wind direction analysis.
        
        Args:
            segments: DataFrame with sailing segments
            wind_direction: Wind direction in degrees
            
        Returns:
            Updated DataFrame with wind analysis
        """
        if segments.empty:
            return segments
            
        logger.info(f"Updating {len(segments)} segments with wind direction {wind_direction}°")
        
        try:
            # Re-analyze with new wind direction
            updated = analyze_wind_angles(segments.copy(), wind_direction)
            return updated
            
        except Exception as e:
            logger.error(f"Error updating segments with wind: {e}")
            return segments
    
    @staticmethod
    def analyze_wind_performance(
        segments: pd.DataFrame,
        wind_direction: float
    ) -> Dict[str, Any]:
        """
        Analyze wind performance metrics from segments.
        
        Args:
            segments: DataFrame with wind-analyzed segments
            wind_direction: Wind direction used for analysis
            
        Returns:
            Dictionary with wind performance metrics
        """
        if segments.empty or 'angle_to_wind' not in segments.columns:
            return {}
        
        summary = {
            'wind_direction': wind_direction,
            'total_segments': len(segments),
            'avg_angle_to_wind': segments['angle_to_wind'].mean()
        }
        
        # Upwind vs downwind analysis
        upwind = segments[segments['angle_to_wind'] < 90]
        downwind = segments[segments['angle_to_wind'] >= 90]
        
        summary['upwind_segments'] = len(upwind)
        summary['downwind_segments'] = len(downwind)
        
        if not upwind.empty:
            summary['avg_upwind_angle'] = upwind['angle_to_wind'].mean()
            summary['best_upwind_angle'] = upwind['angle_to_wind'].min()
        
        if not downwind.empty:
            summary['avg_downwind_angle'] = downwind['angle_to_wind'].mean()
        
        # Tack analysis
        if 'tack' in segments.columns:
            port_segments = segments[segments['tack'] == 'Port']
            starboard_segments = segments[segments['tack'] == 'Starboard']
            
            summary['port_segments'] = len(port_segments)
            summary['starboard_segments'] = len(starboard_segments)
            
            if not port_segments.empty:
                summary['port_avg_angle'] = port_segments['angle_to_wind'].mean()
                
            if not starboard_segments.empty:
                summary['starboard_avg_angle'] = starboard_segments['angle_to_wind'].mean()
        
        # Sailing type distribution
        if 'sailing_type' in segments.columns:
            sailing_types = segments['sailing_type'].value_counts()
            summary['sailing_type_distribution'] = sailing_types.to_dict()
        
        return summary
    
    @staticmethod
    def validate_wind_direction(wind_direction: float) -> float:
        """
        Validate and normalize wind direction.
        
        Args:
            wind_direction: Wind direction in degrees
            
        Returns:
            Normalized wind direction (0-359)
        """
        if not isinstance(wind_direction, (int, float)):
            logger.warning(f"Invalid wind direction type: {type(wind_direction)}, defaulting to 90°")
            return 90.0
            
        if pd.isna(wind_direction):
            logger.warning("NaN wind direction, defaulting to 90°")
            return 90.0
        
        # Normalize to 0-359 range
        normalized = float(wind_direction) % 360.0
        
        if normalized != wind_direction:
            logger.info(f"Normalized wind direction: {wind_direction}° → {normalized}°")
            
        return normalized


# Convenience functions for common operations
def estimate_wind_from_segments(
    segments: pd.DataFrame,
    initial_wind: float,
    method: str = "iterative",
    suspicious_angle_threshold: float = 20.0
) -> WindEstimate:
    """
    Convenience function for wind estimation.
    
    Args:
        segments: DataFrame with sailing segments
        initial_wind: Initial wind direction estimate
        method: Estimation method to use
        suspicious_angle_threshold: Threshold for filtering suspicious angles
        
    Returns:
        WindEstimate result
    """
    params = WindAnalysisParams(
        initial_wind_direction=initial_wind,
        suspicious_angle_threshold=suspicious_angle_threshold,
        estimation_method=method
    )
    
    service = PureWindAnalysisService()
    return service.estimate_wind_direction(segments, params)


def update_segments_wind_analysis(
    segments: pd.DataFrame,
    wind_direction: float
) -> pd.DataFrame:
    """
    Convenience function for updating segments with wind analysis.
    
    Args:
        segments: DataFrame with sailing segments
        wind_direction: Wind direction in degrees
        
    Returns:
        Updated DataFrame with wind analysis
    """
    service = PureWindAnalysisService()
    return service.update_segments_with_wind(segments, wind_direction)