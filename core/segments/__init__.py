"""
Segments package.

This package contains functionality for segment detection, analysis, and filtering.
Now with clean, modular structure and no circular dependencies.
"""

# Import from the new modular detector
from .detector import (
    find_consistent_angle_stretches,
    calculate_point_metrics,
    detect_angle_changes,
    build_segments,
    filter_valid_segments,
    analyze_segment_distribution
)

# Import from analyzer (if it exists)
try:
    from .analyzer import SegmentAnalyzer, SegmentFilterCriteria
except ImportError:
    # analyzer module doesn't exist yet
    pass

# Import wind analysis function from calculations (no circular dependency!)
from core.calculations import analyze_wind_angles

# Import segment models
from core.models.segment import Segment, segments_to_dataframe, dataframe_to_segments

__all__ = [
    # Main detection function (backward compatible)
    'find_consistent_angle_stretches',
    
    # Modular detection functions
    'calculate_point_metrics',
    'detect_angle_changes', 
    'build_segments',
    'filter_valid_segments',
    'analyze_segment_distribution',
    
    # Wind analysis
    'analyze_wind_angles',
    
    # Models
    'Segment',
    'segments_to_dataframe',
    'dataframe_to_segments',
    
    # Analyzer (if available)
    'SegmentAnalyzer',
    'SegmentFilterCriteria'
]