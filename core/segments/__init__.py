"""
Segments package.

This package contains functionality for segment detection, analysis, and filtering.
"""

# Import from analyzer module
from core.segments.analyzer import SegmentAnalyzer, SegmentFilterCriteria

# Import the original segments.py module functions to maintain backward compatibility
import sys
import importlib.util
import os

# Get the absolute path to segments.py using the package's directory
package_dir = os.path.dirname(__file__)
segments_path = os.path.join(os.path.dirname(package_dir), 'segments.py')

# Load the segments.py module
spec = importlib.util.spec_from_file_location('core.segments_module', segments_path)
segments_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(segments_module)

# Re-export the functions from segments.py
find_consistent_angle_stretches = segments_module.find_consistent_angle_stretches
analyze_wind_angles = segments_module.analyze_wind_angles

# Clean up
del sys, importlib, os, package_dir, segments_path, spec, segments_module