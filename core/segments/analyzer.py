"""
Segment analyzer module.

This module provides functionality for analyzing track segments,
including quality scoring, filtering, and statistical analysis.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass

from config.settings import (
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_MIN_SEGMENT_DISTANCE,
    DEFAULT_MIN_POINTS_FOR_SEGMENT
)

logger = logging.getLogger(__name__)

@dataclass
class SegmentFilterCriteria:
    """Criteria for filtering segments."""
    min_angle_to_wind: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    min_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE
    min_duration: float = 0.0
    min_speed: float = 0.0
    max_speed: Optional[float] = None
    tack: Optional[str] = None  # 'Port', 'Starboard', or None for both
    upwind_downwind: Optional[str] = None  # 'Upwind', 'Downwind', or None for both


class SegmentAnalyzer:
    """
    Analyzer for track segments.
    
    This class provides methods for analyzing, filtering, and scoring
    track segments to identify the most reliable and useful data.
    """
    
    def __init__(self, segments: pd.DataFrame):
        """
        Initialize the analyzer with segments.
        
        Args:
            segments: DataFrame with segments to analyze
        """
        self.segments = segments.copy()
    
    def filter_segments(self, criteria: SegmentFilterCriteria) -> pd.DataFrame:
        """
        Filter segments based on the provided criteria.
        
        Args:
            criteria: Filtering criteria
            
        Returns:
            DataFrame: Filtered segments
        """
        result = self.segments.copy()
        
        # Apply each filter criterion
        if 'angle_to_wind' in result.columns and criteria.min_angle_to_wind > 0:
            result = result[result['angle_to_wind'] >= criteria.min_angle_to_wind]
        
        if 'distance' in result.columns and criteria.min_distance > 0:
            result = result[result['distance'] >= criteria.min_distance]
        
        if 'duration' in result.columns and criteria.min_duration > 0:
            result = result[result['duration'] >= criteria.min_duration]
        
        if 'speed' in result.columns and criteria.min_speed > 0:
            result = result[result['speed'] >= criteria.min_speed]
        
        if 'speed' in result.columns and criteria.max_speed is not None:
            result = result[result['speed'] <= criteria.max_speed]
        
        if 'tack' in result.columns and criteria.tack is not None:
            result = result[result['tack'] == criteria.tack]
        
        if 'upwind_downwind' in result.columns and criteria.upwind_downwind is not None:
            result = result[result['upwind_downwind'] == criteria.upwind_downwind]
        
        logger.info(f"Filtered segments: {len(self.segments)} -> {len(result)} segments")
        return result
    
    def calculate_quality_scores(self) -> pd.DataFrame:
        """
        Calculate quality scores for segments.
        
        The quality score is a weighted combination of:
        - Distance (50%): Longer segments are more reliable
        - Speed consistency (30%): Segments with consistent speed are more reliable
        - Duration (20%): Longer duration segments are more reliable
        
        Returns:
            DataFrame: Segments with added quality_score column
        """
        # Make a copy to avoid modifying the original
        result = self.segments.copy()
        
        # Ensure we have the necessary columns
        required_columns = ['distance', 'speed', 'duration']
        missing_columns = [col for col in required_columns if col not in result.columns]
        if missing_columns:
            logger.warning(f"Missing columns for quality scoring: {missing_columns}")
            return result
        
        # Normalize each metric to 0-1 range
        if len(result) > 0:
            # Distance normalization - higher is better
            distance_max = result['distance'].max()
            if distance_max > 0:
                result['distance_norm'] = result['distance'] / distance_max
            else:
                result['distance_norm'] = 0
            
            # Duration normalization - higher is better
            duration_max = result['duration'].max()
            if duration_max > 0:
                result['duration_norm'] = result['duration'] / duration_max
            else:
                result['duration_norm'] = 0
            
            # Speed consistency - use coefficient of variation if we have per-point data
            # Otherwise, just use normalized speed
            speed_max = result['speed'].max()
            if speed_max > 0:
                result['speed_norm'] = result['speed'] / speed_max
            else:
                result['speed_norm'] = 0
            
            # Calculate final score
            result['quality_score'] = (
                result['distance_norm'] * 0.5 +
                result['speed_norm'] * 0.3 +
                result['duration_norm'] * 0.2
            )
            
            # Cleanup temporary columns
            result = result.drop(['distance_norm', 'speed_norm', 'duration_norm'], axis=1)
        
        return result
    
    def detect_suspicious_segments(self, angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD) -> pd.DataFrame:
        """
        Detect suspicious segments based on angle to wind.
        
        Args:
            angle_threshold: Minimum angle to wind that is considered physically possible
            
        Returns:
            DataFrame: Segments with added suspicious column
        """
        result = self.segments.copy()
        
        # Ensure we have the angle_to_wind column
        if 'angle_to_wind' not in result.columns:
            logger.warning("angle_to_wind column missing, cannot detect suspicious segments")
            result['suspicious'] = False
            return result
        
        # Mark segments with angle_to_wind less than threshold as suspicious
        result['suspicious'] = result['angle_to_wind'] < angle_threshold
        
        suspicious_count = result['suspicious'].sum()
        logger.info(f"Detected {suspicious_count} suspicious segments out of {len(result)}")
        
        return result
    
    def find_best_segments(self, column: str, maximize: bool = False, limit: int = 5) -> pd.DataFrame:
        """
        Find the best segments according to a column value.
        
        Args:
            column: Column to sort by
            maximize: If True, find maximum values, otherwise minimum
            limit: Maximum number of segments to return
            
        Returns:
            DataFrame: Best segments
        """
        if column not in self.segments.columns:
            logger.warning(f"Column {column} not found in segments")
            return pd.DataFrame()
        
        # Sort segments
        if maximize:
            sorted_segments = self.segments.sort_values(column, ascending=False)
        else:
            sorted_segments = self.segments.sort_values(column, ascending=True)
        
        # Return top segments
        return sorted_segments.head(limit)
    
    def calculate_segment_groups(self) -> Dict[str, pd.DataFrame]:
        """
        Group segments by tack and upwind/downwind.
        
        Returns:
            Dict: Dictionary mapping group names to segment DataFrames
        """
        result = {}
        
        # Ensure we have the necessary columns
        if 'tack' not in self.segments.columns or 'upwind_downwind' not in self.segments.columns:
            logger.warning("tack or upwind_downwind columns missing, cannot group segments")
            return result
        
        # Group by tack
        port_tack = self.segments[self.segments['tack'] == 'Port']
        starboard_tack = self.segments[self.segments['tack'] == 'Starboard']
        result['port'] = port_tack
        result['starboard'] = starboard_tack
        
        # Group by upwind/downwind
        upwind = self.segments[self.segments['upwind_downwind'] == 'Upwind']
        downwind = self.segments[self.segments['upwind_downwind'] == 'Downwind']
        result['upwind'] = upwind
        result['downwind'] = downwind
        
        # Group by combination
        port_upwind = port_tack[port_tack['upwind_downwind'] == 'Upwind']
        port_downwind = port_tack[port_tack['upwind_downwind'] == 'Downwind']
        starboard_upwind = starboard_tack[starboard_tack['upwind_downwind'] == 'Upwind']
        starboard_downwind = starboard_tack[starboard_tack['upwind_downwind'] == 'Downwind']
        result['port_upwind'] = port_upwind
        result['port_downwind'] = port_downwind
        result['starboard_upwind'] = starboard_upwind
        result['starboard_downwind'] = starboard_downwind
        
        return result
    
    def analyze_tack_balance(self) -> Dict[str, Any]:
        """
        Analyze the balance between port and starboard tacks.
        
        Returns:
            Dict: Analysis results
        """
        groups = self.calculate_segment_groups()
        
        port_count = len(groups.get('port', pd.DataFrame()))
        starboard_count = len(groups.get('starboard', pd.DataFrame()))
        total_count = port_count + starboard_count
        
        if total_count > 0:
            port_percentage = port_count / total_count * 100
            starboard_percentage = starboard_count / total_count * 100
        else:
            port_percentage = 0
            starboard_percentage = 0
        
        # Calculate distance sailed on each tack
        port_distance = groups.get('port', pd.DataFrame())['distance'].sum() if 'distance' in self.segments.columns else 0
        starboard_distance = groups.get('starboard', pd.DataFrame())['distance'].sum() if 'distance' in self.segments.columns else 0
        total_distance = port_distance + starboard_distance
        
        if total_distance > 0:
            port_distance_percentage = port_distance / total_distance * 100
            starboard_distance_percentage = starboard_distance / total_distance * 100
        else:
            port_distance_percentage = 0
            starboard_distance_percentage = 0
        
        return {
            'port_count': port_count,
            'starboard_count': starboard_count,
            'total_count': total_count,
            'port_percentage': port_percentage,
            'starboard_percentage': starboard_percentage,
            'port_distance': port_distance,
            'starboard_distance': starboard_distance,
            'total_distance': total_distance,
            'port_distance_percentage': port_distance_percentage,
            'starboard_distance_percentage': starboard_distance_percentage,
            'is_balanced_count': 0.33 <= port_percentage / 100 <= 0.67 if total_count > 0 else False,
            'is_balanced_distance': 0.33 <= port_distance_percentage / 100 <= 0.67 if total_distance > 0 else False
        }
    
    def analyze_angle_distribution(self) -> Dict[str, Any]:
        """
        Analyze the distribution of angles to wind.
        
        Returns:
            Dict: Analysis results
        """
        if 'angle_to_wind' not in self.segments.columns:
            logger.warning("angle_to_wind column missing, cannot analyze angle distribution")
            return {}
        
        # Calculate statistics for the full dataset
        angles = self.segments['angle_to_wind']
        
        result = {
            'min_angle': angles.min(),
            'max_angle': angles.max(),
            'mean_angle': angles.mean(),
            'median_angle': angles.median(),
            'std_dev': angles.std(),
            'quartile_25': angles.quantile(0.25),
            'quartile_75': angles.quantile(0.75)
        }
        
        # Add separate upwind and downwind statistics
        groups = self.calculate_segment_groups()
        
        if 'upwind' in groups and not groups['upwind'].empty:
            upwind_angles = groups['upwind']['angle_to_wind']
            result['upwind_min_angle'] = upwind_angles.min()
            result['upwind_max_angle'] = upwind_angles.max()
            result['upwind_mean_angle'] = upwind_angles.mean()
            result['upwind_median_angle'] = upwind_angles.median()
        
        if 'downwind' in groups and not groups['downwind'].empty:
            downwind_angles = groups['downwind']['angle_to_wind']
            result['downwind_min_angle'] = downwind_angles.min()
            result['downwind_max_angle'] = downwind_angles.max()
            result['downwind_mean_angle'] = downwind_angles.mean()
            result['downwind_median_angle'] = downwind_angles.median()
        
        return result