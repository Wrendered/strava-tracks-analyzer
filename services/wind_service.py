"""
Wind analysis service.

This module provides business logic for wind direction estimation and related calculations,
separating these concerns from UI components.
"""

import pandas as pd
import numpy as np
import logging
import math
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass

from utils.state_manager import StateManager, WindStateManager
from core.wind.estimate import estimate_wind_direction
from core.wind.models import WindEstimate
from core.metrics_advanced import (
    calculate_vmg_upwind,
    calculate_vmg_downwind,
    estimate_wind_direction_weighted
)
from config.settings import (
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_WIND_DIRECTION
)

# Advanced algorithm configuration
DEFAULT_MIN_SEGMENT_DISTANCE = 50  # Minimum segment distance for algorithms in meters
DEFAULT_VMG_ANGLE_RANGE = 20       # Range around best angle to include for VMG calculation

logger = logging.getLogger(__name__)

@dataclass
class WindAnalysisParams:
    """Parameters for wind analysis."""
    initial_wind_direction: float = DEFAULT_WIND_DIRECTION
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE
    vmg_angle_range: float = DEFAULT_VMG_ANGLE_RANGE


class WindService:
    """
    Service for wind analysis and related calculations.
    
    This class centralizes the business logic for wind direction estimation,
    VMG calculations, and other wind-related functionality.
    """
    
    @staticmethod
    def update_wind_direction(new_wind_direction: float, recalculate_stretches: bool = True) -> bool:
        """
        Update wind direction and optionally recalculate segments.
        
        Args:
            new_wind_direction: The new wind direction to set
            recalculate_stretches: Whether to recalculate stretches with the new wind direction
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        # Import directly from the core.segments package
        from core.segments import analyze_wind_angles
        from services.segment_service import SegmentService
        
        # Store the previous wind direction for logging
        prev_wind = WindStateManager.get_wind_direction()
        
        # Update the wind direction in session state
        WindStateManager.set_wind_direction(new_wind_direction)
        
        # Log the change
        if prev_wind is not None and prev_wind != new_wind_direction:
            logger.info(f"Wind direction updated: {prev_wind}° → {new_wind_direction}°")
        else:
            logger.info(f"Wind direction set to: {new_wind_direction}°")
        
        # If we don't need to recalculate stretches or don't have any, we're done
        track_stretches = StateManager.get('track_stretches')
        if not recalculate_stretches or track_stretches is None:
            return True
        
        # If we have track data, use the segment service to recalculate
        track_data = StateManager.get('track_data')
        if track_data is not None:
            return SegmentService.recalculate_segments("wind direction")
        
        # Fallback: try to update existing stretches directly
        try:
            recalculated = analyze_wind_angles(track_stretches, new_wind_direction)
            StateManager.set('track_stretches', recalculated)
            logger.info(f"Updated existing stretches with wind direction {new_wind_direction}°")
            return True
        except Exception as e:
            logger.error(f"Error updating existing stretches: {e}")
            return False
    
    @staticmethod
    def estimate_wind_direction(
        segments: pd.DataFrame,
        params: Optional[WindAnalysisParams] = None,
        method: str = "weighted"
    ) -> WindEstimate:
        """
        Estimate wind direction from segments using the specified method.
        
        Args:
            segments: DataFrame with segments
            params: Parameters for wind analysis, or None to use defaults
            method: Estimation method ("weighted", "iterative", or "basic")
            
        Returns:
            WindEstimate: Object with estimated wind direction and confidence
        """
        if params is None:
            params = WindAnalysisParams(
                initial_wind_direction=WindStateManager.get_wind_direction(),
                suspicious_angle_threshold=StateManager.get(
                    'suspicious_angle_threshold', DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD),
                min_segment_distance=DEFAULT_MIN_SEGMENT_DISTANCE,
                vmg_angle_range=DEFAULT_VMG_ANGLE_RANGE
            )
        
        # Use the appropriate estimation method
        if method == "weighted":
            result = estimate_wind_direction_weighted(
                segments.copy(),
                params.initial_wind_direction,
                suspicious_angle_threshold=params.suspicious_angle_threshold,
                min_segment_distance=params.min_segment_distance
            )
        elif method == "iterative":
            result = estimate_wind_direction(
                segments.copy(),
                params.initial_wind_direction,
                method="iterative",
                suspicious_angle_threshold=params.suspicious_angle_threshold
            )
        else:
            result = estimate_wind_direction(
                segments.copy(),
                params.initial_wind_direction,
                method="basic",
                suspicious_angle_threshold=params.suspicious_angle_threshold
            )
        
        return result
    
    @staticmethod
    def calculate_vmg_upwind(
        upwind_segments: pd.DataFrame,
        params: Optional[WindAnalysisParams] = None
    ) -> Optional[float]:
        """
        Calculate VMG (velocity made good) upwind.
        
        Args:
            upwind_segments: DataFrame with upwind segments
            params: Parameters for VMG calculation, or None to use defaults
            
        Returns:
            float: VMG upwind in knots, or None if calculation failed
        """
        if params is None:
            params = WindAnalysisParams(
                min_segment_distance=DEFAULT_MIN_SEGMENT_DISTANCE,
                vmg_angle_range=DEFAULT_VMG_ANGLE_RANGE
            )
        
        # Use the advanced weighted algorithm
        return calculate_vmg_upwind(
            upwind_segments,
            angle_range=params.vmg_angle_range,
            min_segment_distance=params.min_segment_distance
        )
    
    @staticmethod
    def calculate_vmg_downwind(
        downwind_segments: pd.DataFrame,
        params: Optional[WindAnalysisParams] = None
    ) -> Optional[float]:
        """
        Calculate VMG (velocity made good) downwind.
        
        Args:
            downwind_segments: DataFrame with downwind segments
            params: Parameters for VMG calculation, or None to use defaults
            
        Returns:
            float: VMG downwind in knots, or None if calculation failed
        """
        if params is None:
            params = WindAnalysisParams(
                min_segment_distance=DEFAULT_MIN_SEGMENT_DISTANCE,
                vmg_angle_range=DEFAULT_VMG_ANGLE_RANGE
            )
        
        # Use the advanced weighted algorithm
        return calculate_vmg_downwind(
            downwind_segments,
            angle_range=params.vmg_angle_range,
            min_segment_distance=params.min_segment_distance
        )
    
    @staticmethod
    def calculate_fallback_vmg_upwind(best_port: pd.Series, best_starboard: pd.Series) -> float:
        """
        Calculate a fallback VMG upwind when advanced algorithm cannot be used.
        
        Args:
            best_port: Best port tack segment
            best_starboard: Best starboard tack segment
            
        Returns:
            float: Fallback VMG upwind in knots
        """
        # Average the angles
        pointing_power = (best_port['angle_to_wind'] + best_starboard['angle_to_wind']) / 2
        
        # Average speed
        avg_upwind_speed = (best_port['speed'] + best_starboard['speed']) / 2
        
        # Calculate upwind progress speed
        return avg_upwind_speed * math.cos(math.radians(pointing_power))
    
    @staticmethod
    def get_angle_difference(best_port: pd.Series, best_starboard: pd.Series) -> float:
        """
        Calculate the difference between port and starboard angles.
        
        Args:
            best_port: Best port tack segment
            best_starboard: Best starboard tack segment
            
        Returns:
            float: Absolute angle difference in degrees
        """
        return abs(best_port['angle_to_wind'] - best_starboard['angle_to_wind'])
    
    @staticmethod
    def get_combined_angle(best_port: pd.Series, best_starboard: pd.Series) -> float:
        """
        Calculate the combined angle from port and starboard.
        
        Args:
            best_port: Best port tack segment
            best_starboard: Best starboard tack segment
            
        Returns:
            float: Combined angle in degrees
        """
        return (best_port['angle_to_wind'] + best_starboard['angle_to_wind']) / 2