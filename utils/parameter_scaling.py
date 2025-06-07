"""
Parameter scaling utilities for track analysis
"""
from dataclasses import dataclass
import pandas as pd
from core.constants import DEFAULT_MIN_SEGMENT_DISTANCE_METERS, MIN_TIME_BASE_SECONDS, DEFAULT_ANGLE_TOLERANCE_DEGREES


@dataclass
class SegmentationParams:
    """
    Class representing segmentation parameters for track analysis.
    """
    min_distance: float
    min_time: float
    max_angle_tolerance: float
    
    @classmethod
    def calculate_adaptive(cls, track: pd.DataFrame) -> 'SegmentationParams':
        """
        Calculate adaptive segmentation parameters based on track characteristics.
        
        For long tracks (>3 hours), scales parameters to avoid over-segmentation.
        
        Args:
            track: DataFrame containing track data
            
        Returns:
            SegmentationParams with adaptive values
        """
        # Start with base parameters
        min_distance = DEFAULT_MIN_SEGMENT_DISTANCE_METERS
        min_time = MIN_TIME_BASE_SECONDS
        max_angle_tolerance = DEFAULT_ANGLE_TOLERANCE_DEGREES
        
        # Check if we have time data for duration calculation
        if 'time' in track.columns and len(track) > 0:
            track_duration_hours = (track['time'].max() - track['time'].min()).total_seconds() / 3600
            
            # For tracks longer than 3 hours, scale parameters to prevent over-segmentation
            if track_duration_hours > 3:
                # Scale factor increases gradually for very long tracks
                scale_factor = 1 + (track_duration_hours - 3) * 0.2
                
                min_distance *= scale_factor
                min_time *= scale_factor
                # Scale angle tolerance more conservatively
                max_angle_tolerance *= (1 + (scale_factor - 1) * 0.3)
        
        return cls(
            min_distance=min_distance,
            min_time=min_time,
            max_angle_tolerance=max_angle_tolerance
        )
    
    def scale(self, factor: float) -> 'SegmentationParams':
        """
        Scale parameters by a given factor.
        
        Args:
            factor: Scaling factor to apply to parameters
            
        Returns:
            New SegmentationParams with scaled values
        """
        return SegmentationParams(
            min_distance=self.min_distance * factor,
            min_time=self.min_time * factor,
            # Scale angle tolerance more conservatively
            max_angle_tolerance=self.max_angle_tolerance * (1 + (factor - 1) * 0.5)
        )