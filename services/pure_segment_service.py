"""
Pure segment analysis service without external dependencies.

This module provides clean business logic for segment detection and analysis,
with no dependencies on UI frameworks or state management.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from datetime import timedelta

# Import the functions directly from the core.segments package
from core.segments import find_consistent_angle_stretches
from core.calculations import analyze_wind_angles
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


class PureSegmentService:
    """
    Pure segment service with no external dependencies.
    
    This service provides clean business logic for working with track segments,
    without any coupling to UI frameworks or state management systems.
    """
    
    @staticmethod
    def detect_segments(
        track_data: pd.DataFrame, 
        params: SegmentDetectionParams
    ) -> pd.DataFrame:
        """
        Detect consistent angle segments in track data.
        
        Args:
            track_data: DataFrame with track data
            params: Parameters for segment detection
            
        Returns:
            DataFrame with detected segments
        """
        logger.info(f"Detecting segments with tolerance={params.angle_tolerance}°, "
                   f"min_duration={params.min_duration}s, min_distance={params.min_distance}m")
        
        # Detect segments
        segments = find_consistent_angle_stretches(
            track_data, 
            params.angle_tolerance,
            params.min_duration,
            params.min_distance
        )
        
        if segments.empty:
            logger.warning("No segments detected with current parameters")
            return segments
            
        # Apply speed filtering
        if 'avg_speed_knots' in segments.columns:
            segments = segments[segments['avg_speed_knots'] >= params.min_speed]
            logger.info(f"After speed filtering (≥{params.min_speed} knots): {len(segments)} segments")
        
        return segments
    
    @staticmethod
    def analyze_segments_with_wind(
        segments: pd.DataFrame,
        wind_direction: float,
        suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    ) -> pd.DataFrame:
        """
        Analyze segments with wind direction to determine tacks and sailing types.
        
        Args:
            segments: DataFrame with detected segments
            wind_direction: Wind direction in degrees
            suspicious_angle_threshold: Threshold for suspicious angles
            
        Returns:
            DataFrame with wind analysis added
        """
        if segments.empty:
            return segments
            
        logger.info(f"Analyzing {len(segments)} segments with wind direction {wind_direction}°")
        
        # Apply wind analysis
        analyzed = analyze_wind_angles(segments, wind_direction)
        
        # Filter out suspicious angles if requested
        if suspicious_angle_threshold > 0:
            suspicious = analyzed['angle_to_wind'] < suspicious_angle_threshold
            if suspicious.any():
                logger.info(f"Filtering {suspicious.sum()} segments with suspicious angles "
                           f"< {suspicious_angle_threshold}°")
                analyzed = analyzed[~suspicious]
        
        return analyzed
    
    @staticmethod
    def filter_segments_by_criteria(
        segments: pd.DataFrame,
        min_distance: Optional[float] = None,
        min_duration: Optional[float] = None,
        min_speed: Optional[float] = None,
        angle_range: Optional[Tuple[float, float]] = None
    ) -> pd.DataFrame:
        """
        Filter segments by various criteria.
        
        Args:
            segments: DataFrame with segments
            min_distance: Minimum distance filter
            min_duration: Minimum duration filter  
            min_speed: Minimum speed filter
            angle_range: (min_angle, max_angle) range for angle_to_wind
            
        Returns:
            Filtered DataFrame
        """
        if segments.empty:
            return segments
            
        filtered = segments.copy()
        initial_count = len(filtered)
        
        if min_distance is not None:
            filtered = filtered[filtered['distance'] >= min_distance]
            
        if min_duration is not None:
            filtered = filtered[filtered['duration'] >= min_duration]
            
        if min_speed is not None and 'avg_speed_knots' in filtered.columns:
            filtered = filtered[filtered['avg_speed_knots'] >= min_speed]
            
        if angle_range is not None and 'angle_to_wind' in filtered.columns:
            min_angle, max_angle = angle_range
            filtered = filtered[
                (filtered['angle_to_wind'] >= min_angle) & 
                (filtered['angle_to_wind'] <= max_angle)
            ]
        
        logger.info(f"Filtered segments: {initial_count} → {len(filtered)}")
        return filtered
    
    @staticmethod
    def get_segment_summary(segments: pd.DataFrame) -> Dict[str, Any]:
        """
        Get summary statistics for segments.
        
        Args:
            segments: DataFrame with segments
            
        Returns:
            Dictionary with summary statistics
        """
        if segments.empty:
            return {
                'total_segments': 0,
                'total_distance': 0,
                'total_duration': 0,
                'avg_speed': 0
            }
        
        summary = {
            'total_segments': len(segments),
            'total_distance': segments['distance'].sum(),
            'total_duration': segments['duration'].sum(),
            'avg_speed': segments.get('avg_speed_knots', pd.Series([0])).mean()
        }
        
        # Add tack distribution if available
        if 'tack' in segments.columns:
            tack_counts = segments['tack'].value_counts()
            summary['tack_distribution'] = tack_counts.to_dict()
        
        # Add sailing type distribution if available  
        if 'sailing_type' in segments.columns:
            sailing_counts = segments['sailing_type'].value_counts()
            summary['sailing_distribution'] = sailing_counts.to_dict()
            
        return summary