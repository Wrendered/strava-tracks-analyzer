"""
Pure wind estimation service without external dependencies.

This module provides clean business logic for wind direction estimation,
with no dependencies on UI frameworks or state management.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass

from core.wind.estimate import estimate_wind_direction
from core.wind.models import WindEstimate
from core.wind.algorithms import estimate_wind_direction_iterative
from core.calculations import analyze_wind_angles
from config.settings import DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD

logger = logging.getLogger(__name__)

@dataclass
class WindEstimationParams:
    """Parameters for wind estimation."""
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    max_iterations: int = 5
    use_iterative: bool = True


class PureWindService:
    """
    Pure wind service with no external dependencies.
    
    This service provides clean business logic for wind direction estimation,
    without any coupling to UI frameworks or state management systems.
    """
    
    @staticmethod
    def estimate_wind_direction(
        segments: pd.DataFrame,
        initial_wind_direction: float,
        params: Optional[WindEstimationParams] = None
    ) -> WindEstimate:
        """
        Estimate wind direction from segments.
        
        Args:
            segments: DataFrame with sailing segments
            initial_wind_direction: Initial wind direction estimate
            params: Parameters for wind estimation
            
        Returns:
            WindEstimate object with direction and confidence
        """
        if params is None:
            params = WindEstimationParams()
            
        if segments.empty:
            logger.warning("No segments provided for wind estimation")
            return WindEstimate(
                direction=initial_wind_direction,
                confidence="None",
                port_average_angle=0,
                starboard_average_angle=0,
                total_segments=0,
                port_segments=0,
                starboard_segments=0
            )
        
        logger.info(f"Estimating wind direction from {len(segments)} segments")
        logger.info(f"Initial wind direction: {initial_wind_direction}°")
        
        try:
            if params.use_iterative:
                # Use the iterative algorithm
                result = estimate_wind_direction_iterative(
                    segments,
                    initial_wind_direction,
                    suspicious_angle_threshold=params.suspicious_angle_threshold,
                    max_iterations=params.max_iterations
                )
            else:
                # Use the basic algorithm
                result = estimate_wind_direction(
                    segments,
                    initial_wind_direction,
                    suspicious_angle_threshold=params.suspicious_angle_threshold
                )
            
            logger.info(f"Estimated wind direction: {result.direction:.1f}° "
                       f"(confidence: {result.confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Wind estimation failed: {e}")
            return WindEstimate(
                direction=initial_wind_direction,
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
            segments: DataFrame with segments
            wind_direction: New wind direction
            
        Returns:
            Updated DataFrame with new wind analysis
        """
        if segments.empty:
            return segments
            
        logger.info(f"Updating {len(segments)} segments with wind direction {wind_direction}°")
        
        # Re-analyze with new wind direction
        updated = analyze_wind_angles(segments, wind_direction)
        
        return updated
    
    @staticmethod
    def get_wind_analysis_summary(segments: pd.DataFrame) -> Dict[str, Any]:
        """
        Get summary of wind analysis for segments.
        
        Args:
            segments: DataFrame with wind analysis
            
        Returns:
            Dictionary with wind analysis summary
        """
        if segments.empty or 'angle_to_wind' not in segments.columns:
            return {}
        
        summary = {}
        
        # Overall statistics
        summary['total_segments'] = len(segments)
        summary['avg_angle_to_wind'] = segments['angle_to_wind'].mean()
        summary['wind_direction'] = segments['wind_direction'].iloc[0] if 'wind_direction' in segments.columns else None
        
        # Upwind vs downwind
        upwind = segments[segments['angle_to_wind'] < 90]
        downwind = segments[segments['angle_to_wind'] >= 90]
        
        summary['upwind_segments'] = len(upwind)
        summary['downwind_segments'] = len(downwind)
        
        if len(upwind) > 0:
            summary['avg_upwind_angle'] = upwind['angle_to_wind'].mean()
        
        if len(downwind) > 0:
            summary['avg_downwind_angle'] = downwind['angle_to_wind'].mean()
        
        # Tack analysis
        if 'tack' in segments.columns:
            port_tack = segments[segments['tack'] == 'Port']
            starboard_tack = segments[segments['tack'] == 'Starboard']
            
            summary['port_segments'] = len(port_tack)
            summary['starboard_segments'] = len(starboard_tack)
            
            if len(port_tack) > 0:
                summary['port_avg_angle'] = port_tack['angle_to_wind'].mean()
                
            if len(starboard_tack) > 0:
                summary['starboard_avg_angle'] = starboard_tack['angle_to_wind'].mean()
        
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
            logger.warning(f"Invalid wind direction type: {type(wind_direction)}, defaulting to 0°")
            return 0.0
            
        if pd.isna(wind_direction):
            logger.warning("NaN wind direction, defaulting to 0°")
            return 0.0
        
        # Normalize to 0-359 range
        normalized = float(wind_direction) % 360.0
        
        if normalized != wind_direction:
            logger.info(f"Normalized wind direction: {wind_direction}° → {normalized}°")
            
        return normalized