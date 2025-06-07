"""
Segments package.

This package contains functionality for segment detection and analysis.
Clean, focused interface with no circular dependencies.
"""

# Core segment detection functions
from .detector import (
    find_consistent_angle_stretches,
    calculate_point_metrics,
    detect_angle_changes,
    build_segments,
    filter_valid_segments,
    analyze_segment_distribution
)

# Segment models
from core.models.segment import Segment, segments_to_dataframe, dataframe_to_segments

# Clean public API - only segment detection and models
__all__ = [
    # Main detection function (backward compatible)
    'find_consistent_angle_stretches',
    
    # Modular detection functions
    'calculate_point_metrics',
    'detect_angle_changes', 
    'build_segments',
    'filter_valid_segments',
    'analyze_segment_distribution',
    
    # Models
    'Segment',
    'segments_to_dataframe',
    'dataframe_to_segments',
]