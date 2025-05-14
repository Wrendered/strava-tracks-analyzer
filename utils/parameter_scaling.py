"""
Parameter scaling utilities for track analysis
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import math
import numpy as np
import pandas as pd


@dataclass
class SegmentationParams:
    """
    Class representing segmentation parameters for track analysis.
    """
    min_distance: float
    min_time: float
    max_angle_tolerance: float
    quality_score: float = 1.0
    
    @classmethod
    def calculate_optimal(cls, track: pd.DataFrame, ideal_segment_count: int = 20) -> 'SegmentationParams':
        """
        Calculate optimal segmentation parameters based on track characteristics.
        
        Args:
            track: DataFrame containing track data
            ideal_segment_count: Target number of segments (default: 20)
            
        Returns:
            SegmentationParams with calculated optimal values
        """
        # Extract track metadata
        track_duration_minutes = (track['time'].max() - track['time'].min()).total_seconds() / 60
        total_distance = track['distance'].sum() if 'distance' in track.columns else 0
        
        # Base calculation on track duration and total distance
        # Starting with heuristic values
        min_distance = max(10.0, total_distance / (ideal_segment_count * 2))
        min_time = max(5.0, track_duration_minutes * 60 / (ideal_segment_count * 2))
        
        # Calculate heading variance to determine angle tolerance
        if 'heading' in track.columns:
            heading_variance = track['heading'].std()
            max_angle_tolerance = min(30.0, max(5.0, heading_variance * 0.5))
        else:
            max_angle_tolerance = 15.0  # Default value
        
        return cls(
            min_distance=min_distance,
            min_time=min_time,
            max_angle_tolerance=max_angle_tolerance,
            quality_score=1.0  # Start with perfect score
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
            max_angle_tolerance=self.max_angle_tolerance * (1 + (factor - 1) * 0.5),
            quality_score=self.quality_score
        )


def analyze_segmentation_quality(
    stretches: pd.DataFrame, 
    tack_data: pd.DataFrame, 
    min_distance: float, 
    min_time: float, 
    max_angle_tolerance: float
) -> Dict:
    """
    Analyze the quality of segmentation based on current parameters.
    
    Args:
        stretches: DataFrame containing stretch segments
        tack_data: DataFrame containing tack data
        min_distance: Minimum distance parameter used
        min_time: Minimum time parameter used
        max_angle_tolerance: Maximum angle tolerance parameter used
        
    Returns:
        Dict with quality metrics:
            - over_segmentation_score: 0-1 (1 = likely over-segmented)
            - segments_per_tack: Dict of tack to segment count
            - max_segments_per_tack: Maximum segments on any single tack
            - total_segments: Total number of segments
            - ideal_segments: Calculated ideal segment count
            - suggested_params: SegmentationParams for optimal segmentation
    """
    # Count segments per tack
    if tack_data is not None and 'tack' in tack_data.columns:
        tacks = tack_data['tack'].unique()
        segments_per_tack = {tack: len(stretches[stretches['tack'] == tack]) for tack in tacks}
        max_segments_per_tack = max(segments_per_tack.values()) if segments_per_tack else 0
    else:
        segments_per_tack = {}
        max_segments_per_tack = 0
    
    # Check for over-segmentation
    total_segments = len(stretches)
    
    # Calculate track duration and distance
    if 'time' in stretches.columns:
        track_duration = (stretches['time'].max() - stretches['time'].min()).total_seconds() / 60  # in minutes
    else:
        track_duration = 0
        
    track_distance = stretches['distance'].sum() if 'distance' in stretches.columns else 0
    
    # Calculate quality metrics
    # Aim for roughly one segment per 15 minutes, between 5-20 segments total
    ideal_segments = min(20, max(5, track_duration / 15))
    
    # Calculate over-segmentation score (0-1)
    over_segmentation_score = min(1.0, total_segments / ideal_segments) if ideal_segments > 0 else 0
    
    # Only suggest parameter adjustments if over-segmented
    if over_segmentation_score > 0.7 or max_segments_per_tack > 5:
        # Calculate scaling factor based on how over-segmented we are
        scaling_factor = math.log(max(1.5, total_segments / ideal_segments), 10) if ideal_segments > 0 else 1.5
        
        # Create baseline parameters
        current_params = SegmentationParams(
            min_distance=min_distance,
            min_time=min_time,
            max_angle_tolerance=max_angle_tolerance
        )
        
        # Scale parameters
        suggested_params = current_params.scale(scaling_factor)
        suggested_params.quality_score = 1.0 - over_segmentation_score
    else:
        # Parameters are good, no need to adjust
        suggested_params = SegmentationParams(
            min_distance=min_distance,
            min_time=min_time,
            max_angle_tolerance=max_angle_tolerance,
            quality_score=1.0 - over_segmentation_score
        )
    
    return {
        'over_segmentation_score': over_segmentation_score,
        'segments_per_tack': segments_per_tack,
        'max_segments_per_tack': max_segments_per_tack,
        'total_segments': total_segments,
        'ideal_segments': ideal_segments,
        'suggested_params': suggested_params
    }


def apply_optimized_parameters(st, quality_analysis: Dict) -> None:
    """
    Apply optimized parameters automatically in the UI and show notification.
    
    Args:
        st: Streamlit session
        quality_analysis: Dict with quality metrics and suggested parameters
    """
    # Store original parameters for potential revert if not already stored
    if 'original_parameters' not in st.session_state:
        st.session_state.original_parameters = {
            'min_distance': st.session_state.min_distance,
            'min_time': st.session_state.min_time,
            'max_angle_tolerance': st.session_state.max_angle_tolerance
        }
    
    # Apply new parameters
    suggested_params = quality_analysis['suggested_params']
    st.session_state.min_distance = suggested_params.min_distance
    st.session_state.min_time = suggested_params.min_time
    st.session_state.max_angle_tolerance = suggested_params.max_angle_tolerance
    
    # Store quality analysis for reference
    st.session_state.segmentation_quality = quality_analysis
    
    # Trigger recalculation with new parameters
    st.session_state.should_recalculate_segments = True
    
    # Show optimization notification
    st.success(f"Parameters automatically optimized to reduce segments from "
               f"{quality_analysis['total_segments']} to approximately "
               f"{int(quality_analysis['ideal_segments'])}.")