"""
Segment analysis service.

This module provides business logic for segment detection, analysis, and filtering,
separating these concerns from UI components.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from datetime import timedelta

from utils.state_manager import StateManager, SegmentStateManager, WindStateManager
from core.segments import find_consistent_angle_stretches, analyze_wind_angles
from utils.segment_analysis import detect_suspicious_segments
from config.settings import (
    DEFAULT_ANGLE_TOLERANCE,
    DEFAULT_MIN_DURATION,
    DEFAULT_MIN_DISTANCE,
    DEFAULT_MIN_SPEED,
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
)

logger = logging.getLogger(__name__)

@dataclass
class SegmentDetectionParams:
    """Parameters for segment detection and filtering."""
    angle_tolerance: float = DEFAULT_ANGLE_TOLERANCE
    min_duration: float = DEFAULT_MIN_DURATION
    min_distance: float = DEFAULT_MIN_DISTANCE
    min_speed: float = DEFAULT_MIN_SPEED
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD


class SegmentService:
    """
    Service for segment detection, analysis, and filtering.
    
    This class centralizes the business logic for working with track segments,
    providing a clean API that separates concerns from UI components.
    """
    
    @staticmethod
    def detect_segments(
        track_data: pd.DataFrame, 
        params: Optional[SegmentDetectionParams] = None
    ) -> pd.DataFrame:
        """
        Detect consistent angle segments in track data.
        
        Args:
            track_data: DataFrame with track data
            params: Parameters for segment detection, or None to use session state
            
        Returns:
            DataFrame with detected segments
        """
        if params is None:
            # Get params from session state
            param_dict = SegmentStateManager.get_segment_parameters()
            params = SegmentDetectionParams(**param_dict)
            
        logger.info(f"Detecting segments with tolerance={params.angle_tolerance}°, "
                   f"min_duration={params.min_duration}s, min_distance={params.min_distance}m")
        
        # Detect stretches
        stretches = find_consistent_angle_stretches(
            track_data, 
            params.angle_tolerance,
            params.min_duration,
            params.min_distance
        )
        
        # Filter by minimum speed
        if not stretches.empty:
            logger.info(f"Filtering {len(stretches)} stretches by min_speed: {params.min_speed} knots")
            stretches = stretches[stretches['speed'] >= params.min_speed]
            logger.info(f"After filtering: {len(stretches)} stretches remain")
            
        return stretches
    
    @staticmethod
    def analyze_wind_angles_for_segments(
        segments: pd.DataFrame,
        wind_direction: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Analyze wind angles for segments.
        
        Args:
            segments: DataFrame with segments
            wind_direction: Wind direction in degrees, or None to use session state
            
        Returns:
            DataFrame with segments enriched with wind angle information
        """
        if wind_direction is None:
            wind_direction = WindStateManager.get_wind_direction()
            
        # Analyze with current wind direction
        return analyze_wind_angles(segments, wind_direction)
    
    @staticmethod
    def filter_suspicious_segments(
        segments: pd.DataFrame,
        suspicious_angle_threshold: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Filter out suspicious segments.
        
        Args:
            segments: DataFrame with segments
            suspicious_angle_threshold: Threshold for suspicious angles, or None to use session state
            
        Returns:
            DataFrame with suspicious segments removed
        """
        if suspicious_angle_threshold is None:
            suspicious_angle_threshold = StateManager.get(
                'suspicious_angle_threshold', DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD)
            
        return detect_suspicious_segments(segments, suspicious_angle_threshold)
    
    @staticmethod
    def recalculate_segments(params_changed: Optional[str] = None) -> bool:
        """
        Recalculate segments with current parameters from session state.
        
        Args:
            params_changed: Optional string describing which parameters changed (for logging)
            
        Returns:
            bool: True if recalculation was successful, False otherwise
        """
        # Only proceed if we have track data
        track_data = SegmentStateManager.get_track_data()
        if track_data is None:
            return False
        
        try:
            # Get parameters from session state
            param_dict = SegmentStateManager.get_segment_parameters()
            params = SegmentDetectionParams(**param_dict)
            wind_direction = WindStateManager.get_wind_direction()
            
            logger.info(f"Recalculating segments: {params_changed or 'all parameters'} changed")
            logger.info(f"Using parameters: angle_tolerance={params.angle_tolerance}°, "
                      f"min_duration={params.min_duration}s, "
                      f"min_distance={params.min_distance}m, "
                      f"min_speed={params.min_speed}kn, "
                      f"wind_direction={wind_direction}°")
            
            # Re-detect stretches from raw data
            base_stretches = SegmentService.detect_segments(track_data, params)
            
            # Analyze with current wind direction if we have stretches
            if not base_stretches.empty:
                recalculated = SegmentService.analyze_wind_angles_for_segments(base_stretches, wind_direction)
                
                # Update session state
                SegmentStateManager.set_track_stretches(recalculated)
                logger.info(f"Successfully recalculated {len(recalculated)} stretches")
                return True
            else:
                logger.warning("No stretches detected after filtering")
        except Exception as e:
            logger.error(f"Error recalculating segments: {e}")
            
        return False
    
    @staticmethod
    def get_segments_by_upwind_downwind(segments: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split segments into upwind and downwind groups.
        
        Args:
            segments: DataFrame with segments to split
            
        Returns:
            Tuple of (upwind_segments, downwind_segments)
        """
        if 'angle_to_wind' not in segments.columns:
            # If angle_to_wind not present, we can't split
            logger.warning("Cannot split segments by upwind/downwind - angle_to_wind column missing")
            return pd.DataFrame(), pd.DataFrame()
        
        upwind = segments[segments['angle_to_wind'] < 90]
        downwind = segments[segments['angle_to_wind'] >= 90]
        
        return upwind, downwind
    
    @staticmethod
    def get_segments_by_tack(segments: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split segments into port and starboard tack groups.
        
        Args:
            segments: DataFrame with segments to split
            
        Returns:
            Tuple of (port_segments, starboard_segments)
        """
        if 'tack' not in segments.columns:
            # If tack not present, we can't split
            logger.warning("Cannot split segments by tack - tack column missing")
            return pd.DataFrame(), pd.DataFrame()
        
        port = segments[segments['tack'] == 'Port']
        starboard = segments[segments['tack'] == 'Starboard']
        
        return port, starboard
    
    @staticmethod
    def find_best_segments(segments: pd.DataFrame, by_column: str, maximize: bool = False) -> Dict[str, pd.Series]:
        """
        Find best segments by a given column, optionally maximizing or minimizing.
        
        Args:
            segments: DataFrame with segments
            by_column: Column to use for finding best segments
            maximize: If True, find maximum values, otherwise minimum
            
        Returns:
            Dictionary mapping tack names to their best segments
        """
        if by_column not in segments.columns or 'tack' not in segments.columns:
            logger.warning(f"Cannot find best segments - required columns missing")
            return {}
        
        result = {}
        port, starboard = SegmentService.get_segments_by_tack(segments)
        
        # Find best for port tack
        if not port.empty:
            if maximize:
                best_port = port.loc[port[by_column].idxmax()]
            else:
                best_port = port.loc[port[by_column].idxmin()]
            result['Port'] = best_port
        
        # Find best for starboard tack
        if not starboard.empty:
            if maximize:
                best_starboard = starboard.loc[starboard[by_column].idxmax()]
            else:
                best_starboard = starboard.loc[starboard[by_column].idxmin()]
            result['Starboard'] = best_starboard
        
        return result
    
    @staticmethod
    def prepare_segments_for_display(segments: pd.DataFrame, suspicious_angle_threshold: Optional[float] = None) -> pd.DataFrame:
        """
        Prepare segments for display in the UI.
        
        Args:
            segments: DataFrame with segments
            suspicious_angle_threshold: Threshold for suspicious angles
            
        Returns:
            DataFrame with segments prepared for display
        """
        if segments.empty:
            return pd.DataFrame()
        
        if suspicious_angle_threshold is None:
            suspicious_angle_threshold = StateManager.get(
                'suspicious_angle_threshold', DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD)
        
        # Make a copy to avoid modifying the original
        display_df = segments.copy()
        
        # Add original index for reference
        display_df['original_index'] = display_df.index
        display_df = display_df.reset_index()
        
        # Mark suspicious segments
        if 'angle_to_wind' in display_df.columns:
            display_df['suspicious'] = display_df['angle_to_wind'] < suspicious_angle_threshold
        else:
            # If angle_to_wind is missing, we need to recalculate it
            logger.warning("angle_to_wind column missing, cannot mark suspicious segments")
            display_df['suspicious'] = False
        
        # Rename columns for user-friendly display
        display_df = display_df.rename(columns={
            'index': 'segment_id',
            'bearing': 'heading (°)',
            'angle_to_wind': 'angle off wind (°)',
            'distance': 'distance (m)',
            'speed': 'speed (knots)',
            'duration': 'duration (sec)'
        })
        
        # Format values for display
        for col in ['heading (°)', 'angle off wind (°)']:
            if col in display_df.columns:
                display_df[col] = display_df[col].round(1)
        
        if 'distance (m)' in display_df.columns:
            display_df['distance (m)'] = display_df['distance (m)'].round(1)
        
        if 'speed (knots)' in display_df.columns:
            display_df['speed (knots)'] = display_df['speed (knots)'].round(2)
        
        return display_df