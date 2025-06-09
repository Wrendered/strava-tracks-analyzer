"""
Pure segment analysis service with no state dependencies.

This module provides clean business logic for segment detection and analysis
without coupling to UI frameworks or state management systems.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from core.segments import find_consistent_angle_stretches
from core.calculations import analyze_wind_angles
from config.settings import (
    DEFAULT_ANGLE_TOLERANCE, DEFAULT_MIN_DURATION, DEFAULT_MIN_DISTANCE, 
    DEFAULT_MIN_SPEED, DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
)

logger = logging.getLogger(__name__)


@dataclass
class SegmentDetectionParams:
    """Parameters for segment detection."""
    angle_tolerance: float = DEFAULT_ANGLE_TOLERANCE
    min_duration: float = DEFAULT_MIN_DURATION
    min_distance: float = DEFAULT_MIN_DISTANCE
    min_speed: float = DEFAULT_MIN_SPEED
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD


@dataclass
class SegmentAnalysisResult:
    """Result of segment analysis operations."""
    segments: pd.DataFrame
    total_segments: int
    upwind_segments: pd.DataFrame
    downwind_segments: pd.DataFrame
    success: bool
    error_message: Optional[str] = None


class PureSegmentAnalysisService:
    """
    Pure segment analysis service with no external dependencies.
    
    This service provides clean business logic for segment detection and analysis
    without any coupling to UI frameworks or state management systems.
    All data is passed explicitly as parameters.
    """
    
    @staticmethod
    def detect_segments(
        track_data: pd.DataFrame,
        params: SegmentDetectionParams
    ) -> pd.DataFrame:
        """
        Detect consistent angle segments in track data.
        
        Args:
            track_data: DataFrame with GPS track data
            params: Parameters for segment detection
            
        Returns:
            DataFrame with detected segments
        """
        if track_data.empty:
            logger.warning("Empty track data provided for segment detection")
            return pd.DataFrame()
        
        logger.info(f"Detecting segments with tolerance={params.angle_tolerance}°, "
                   f"min_duration={params.min_duration}s, min_distance={params.min_distance}m")
        
        try:
            # Detect segments using core algorithm
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
                initial_count = len(segments)
                segments = segments[segments['avg_speed_knots'] >= params.min_speed]
                logger.info(f"Speed filtering: {initial_count} → {len(segments)} segments "
                           f"(≥{params.min_speed} knots)")
            
            return segments
            
        except Exception as e:
            logger.error(f"Error detecting segments: {e}")
            return pd.DataFrame()
    
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
        
        try:
            # Apply wind analysis
            analyzed = analyze_wind_angles(segments.copy(), wind_direction)
            
            # Filter out suspicious angles if requested
            if suspicious_angle_threshold > 0:
                suspicious = analyzed['angle_to_wind'] < suspicious_angle_threshold
                if suspicious.any():
                    logger.info(f"Filtering {suspicious.sum()} segments with suspicious angles "
                               f"< {suspicious_angle_threshold}°")
                    analyzed = analyzed[~suspicious]
            
            return analyzed
            
        except Exception as e:
            logger.error(f"Error analyzing segments with wind: {e}")
            return segments
    
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
    def get_segments_by_direction(
        segments: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split segments into upwind and downwind groups.
        
        Args:
            segments: DataFrame with wind-analyzed segments
            
        Returns:
            Tuple of (upwind_segments, downwind_segments)
        """
        if segments.empty or 'angle_to_wind' not in segments.columns:
            return pd.DataFrame(), pd.DataFrame()
        
        upwind = segments[segments['angle_to_wind'] < 90]
        downwind = segments[segments['angle_to_wind'] >= 90]
        
        logger.debug(f"Split segments: {len(upwind)} upwind, {len(downwind)} downwind")
        return upwind, downwind
    
    @staticmethod
    def get_segments_by_tack(
        segments: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split segments into port and starboard tacks.
        
        Args:
            segments: DataFrame with tack information
            
        Returns:
            Tuple of (port_segments, starboard_segments)
        """
        if segments.empty or 'tack' not in segments.columns:
            return pd.DataFrame(), pd.DataFrame()
        
        port = segments[segments['tack'] == 'Port']
        starboard = segments[segments['tack'] == 'Starboard']
        
        logger.debug(f"Split segments: {len(port)} port, {len(starboard)} starboard")
        return port, starboard
    
    @staticmethod
    def get_segment_summary(
        segments: pd.DataFrame
    ) -> Dict[str, Any]:
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
        
        # Add direction distribution if available
        if 'direction' in segments.columns:
            direction_counts = segments['direction'].value_counts()
            summary['direction_distribution'] = direction_counts.to_dict()
        
        # Add tack distribution if available
        if 'tack' in segments.columns:
            tack_counts = segments['tack'].value_counts()
            summary['tack_distribution'] = tack_counts.to_dict()
        
        # Add sailing type distribution if available
        if 'sailing_type' in segments.columns:
            sailing_counts = segments['sailing_type'].value_counts()
            summary['sailing_distribution'] = sailing_counts.to_dict()
            
        return summary
    
    @staticmethod
    def find_best_segments(
        segments: pd.DataFrame,
        by_column: str,
        maximize: bool = False
    ) -> Dict[str, pd.Series]:
        """
        Find best segments by specified criteria.
        
        Args:
            segments: DataFrame with segments
            by_column: Column to optimize for
            maximize: Whether to maximize (True) or minimize (False) the column
            
        Returns:
            Dictionary with best segments by category
        """
        if segments.empty or by_column not in segments.columns:
            return {}
        
        results = {}
        
        # Overall best
        if maximize:
            best_idx = segments[by_column].idxmax()
        else:
            best_idx = segments[by_column].idxmin()
        results['overall'] = segments.loc[best_idx]
        
        # Best by tack if available
        if 'tack' in segments.columns:
            for tack in segments['tack'].unique():
                tack_segments = segments[segments['tack'] == tack]
                if not tack_segments.empty:
                    if maximize:
                        best_idx = tack_segments[by_column].idxmax()
                    else:
                        best_idx = tack_segments[by_column].idxmin()
                    results[f'best_{tack.lower()}'] = tack_segments.loc[best_idx]
        
        return results


# Convenience functions for common operations
def detect_track_segments(
    track_data: pd.DataFrame,
    angle_tolerance: float = DEFAULT_ANGLE_TOLERANCE,
    min_duration: float = DEFAULT_MIN_DURATION,
    min_distance: float = DEFAULT_MIN_DISTANCE,
    min_speed: float = DEFAULT_MIN_SPEED
) -> pd.DataFrame:
    """
    Convenience function for segment detection.
    
    Args:
        track_data: DataFrame with GPS track data
        angle_tolerance: Maximum angle variation within segments
        min_duration: Minimum duration for valid segments
        min_distance: Minimum distance for valid segments
        min_speed: Minimum speed for valid segments
        
    Returns:
        DataFrame with detected segments
    """
    params = SegmentDetectionParams(
        angle_tolerance=angle_tolerance,
        min_duration=min_duration,
        min_distance=min_distance,
        min_speed=min_speed
    )
    
    service = PureSegmentAnalysisService()
    return service.detect_segments(track_data, params)


def analyze_segments_complete(
    track_data: pd.DataFrame,
    wind_direction: float,
    detection_params: Optional[SegmentDetectionParams] = None
) -> SegmentAnalysisResult:
    """
    Complete segment analysis pipeline.
    
    Args:
        track_data: DataFrame with GPS track data
        wind_direction: Wind direction for analysis
        detection_params: Optional detection parameters
        
    Returns:
        SegmentAnalysisResult with complete analysis
    """
    if detection_params is None:
        detection_params = SegmentDetectionParams()
    
    service = PureSegmentAnalysisService()
    
    try:
        # Step 1: Detect segments
        segments = service.detect_segments(track_data, detection_params)
        
        if segments.empty:
            return SegmentAnalysisResult(
                segments=segments,
                total_segments=0,
                upwind_segments=pd.DataFrame(),
                downwind_segments=pd.DataFrame(),
                success=False,
                error_message="No segments detected"
            )
        
        # Step 2: Analyze with wind
        analyzed_segments = service.analyze_segments_with_wind(
            segments, wind_direction, detection_params.suspicious_angle_threshold
        )
        
        # Step 3: Split by direction
        upwind, downwind = service.get_segments_by_direction(analyzed_segments)
        
        return SegmentAnalysisResult(
            segments=analyzed_segments,
            total_segments=len(analyzed_segments),
            upwind_segments=upwind,
            downwind_segments=downwind,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Complete segment analysis failed: {e}")
        return SegmentAnalysisResult(
            segments=pd.DataFrame(),
            total_segments=0,
            upwind_segments=pd.DataFrame(),
            downwind_segments=pd.DataFrame(),
            success=False,
            error_message=str(e)
        )