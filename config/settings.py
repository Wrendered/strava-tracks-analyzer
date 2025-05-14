"""
Application settings and constants.

This module centralizes all configuration values and constants used throughout the application,
making it easier to maintain and modify application behavior.
"""

import os
import logging
from typing import Dict, Any

# App information
APP_NAME = "WingWizard"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Analyze wingfoil tracks to improve performance"

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")

# Wind direction settings
DEFAULT_WIND_DIRECTION = 90  # Degrees (East)

# Segment detection parameters - adjusted for better track detection with short tacks
DEFAULT_ANGLE_TOLERANCE = 25  # Degrees - increased from 20° to detect more tacks with variations
DEFAULT_MIN_DURATION = 15  # Seconds - reduced from 20s to capture shorter tacks
DEFAULT_MIN_DISTANCE = 75  # Meters - reduced from 100m for better track coverage
DEFAULT_MIN_SPEED = 8.0  # Knots - lowered from 10.0 to include more valid segments
DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD = 20  # Degrees - angles below this are physically impossible

# Advanced algorithm configuration
DEFAULT_MIN_SEGMENT_DISTANCE = 50  # Minimum segment distance for algorithms in meters
DEFAULT_VMG_ANGLE_RANGE = 20  # Range around best angle to include for VMG calculation
DEFAULT_ACTIVE_SPEED_THRESHOLD = 5.0  # Speeds below this are not considered "active"

# Wind direction estimation parameters
WIND_ESTIMATION_METHODS = ["weighted", "iterative", "basic"]
DEFAULT_WIND_ESTIMATION_METHOD = "weighted"
DEFAULT_MAX_ITERATIONS = 5  # Maximum iterations for iterative wind estimation
DEFAULT_CONVERGENCE_THRESHOLD = 2.0  # Degrees - when to stop iterative estimation

# UI configuration
UI_DEFAULT_PORT_COLOR = "#FF5757"  # Red for port tack
UI_DEFAULT_STARBOARD_COLOR = "#57A0FF"  # Blue for starboard tack
UI_DEFAULT_SUSPICIOUS_COLOR = "#AAAAAA"  # Gray for suspicious segments
UI_DEFAULT_UPWIND_ALPHA = 0.8  # Transparency for upwind segments
UI_DEFAULT_DOWNWIND_ALPHA = 0.5  # Transparency for downwind segments

# Track display parameters
DEFAULT_MAP_ZOOM = 14  # Default zoom level for maps
DEFAULT_TRACK_LINE_WIDTH = 2  # Width of track lines in pixels
DEFAULT_SEGMENT_LINE_WIDTH = 4  # Width of segment lines in pixels

# Data processing parameters
DEFAULT_SMOOTHING_WINDOW = 5  # Points to consider for smoothing GPS tracks
DEFAULT_MAX_SPEED_CUTOFF = 35.0  # Knots - speeds above this are considered errors
DEFAULT_MIN_POINTS_FOR_SEGMENT = 5  # Minimum GPS points required to consider a segment valid

# File parameters
DEFAULT_GPX_POINT_LIMIT = 10000  # Maximum points to process from a GPX file

# Export/Import parameters
EXPORT_VERSION = "1.0"  # Version of export file format

# Gear comparison parameters
DEFAULT_MAX_GEAR_ITEMS = 10  # Maximum number of gear items to compare at once

# Logging configuration
LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    "handlers": [
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, 'app.log'))
    ]
}

# Streamlit page configuration
PAGE_CONFIG = {
    "page_title": "WingWizard - Strava Analyzer",
    "page_icon": "🪂",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        "About": "WingWizard - Analyze your wingfoil tracks to improve performance and have fun doing it!"
    }
}


# =============== Configuration Classes ===============
# These classes provide typed access to configuration sections

class SegmentConfig:
    """Configuration parameters for segment detection and analysis."""
    ANGLE_TOLERANCE = DEFAULT_ANGLE_TOLERANCE
    MIN_DURATION = DEFAULT_MIN_DURATION
    MIN_DISTANCE = DEFAULT_MIN_DISTANCE
    MIN_SPEED = DEFAULT_MIN_SPEED
    SUSPICIOUS_ANGLE_THRESHOLD = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    MIN_SEGMENT_DISTANCE = DEFAULT_MIN_SEGMENT_DISTANCE
    MIN_POINTS = DEFAULT_MIN_POINTS_FOR_SEGMENT
    
    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Get segment configuration as a dictionary."""
        return {
            'angle_tolerance': cls.ANGLE_TOLERANCE,
            'min_duration': cls.MIN_DURATION,
            'min_distance': cls.MIN_DISTANCE,
            'min_speed': cls.MIN_SPEED,
            'suspicious_angle_threshold': cls.SUSPICIOUS_ANGLE_THRESHOLD,
            'min_segment_distance': cls.MIN_SEGMENT_DISTANCE,
            'min_points': cls.MIN_POINTS,
        }


class WindConfig:
    """Configuration parameters for wind analysis."""
    DEFAULT_DIRECTION = DEFAULT_WIND_DIRECTION
    ESTIMATION_METHOD = DEFAULT_WIND_ESTIMATION_METHOD
    MAX_ITERATIONS = DEFAULT_MAX_ITERATIONS
    CONVERGENCE_THRESHOLD = DEFAULT_CONVERGENCE_THRESHOLD
    VMG_ANGLE_RANGE = DEFAULT_VMG_ANGLE_RANGE
    
    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Get wind configuration as a dictionary."""
        return {
            'default_direction': cls.DEFAULT_DIRECTION,
            'estimation_method': cls.ESTIMATION_METHOD,
            'max_iterations': cls.MAX_ITERATIONS,
            'convergence_threshold': cls.CONVERGENCE_THRESHOLD,
            'vmg_angle_range': cls.VMG_ANGLE_RANGE,
        }


class UIConfig:
    """Configuration parameters for UI components."""
    PORT_COLOR = UI_DEFAULT_PORT_COLOR
    STARBOARD_COLOR = UI_DEFAULT_STARBOARD_COLOR
    SUSPICIOUS_COLOR = UI_DEFAULT_SUSPICIOUS_COLOR
    UPWIND_ALPHA = UI_DEFAULT_UPWIND_ALPHA
    DOWNWIND_ALPHA = UI_DEFAULT_DOWNWIND_ALPHA
    MAP_ZOOM = DEFAULT_MAP_ZOOM
    TRACK_LINE_WIDTH = DEFAULT_TRACK_LINE_WIDTH
    SEGMENT_LINE_WIDTH = DEFAULT_SEGMENT_LINE_WIDTH
    
    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Get UI configuration as a dictionary."""
        return {
            'port_color': cls.PORT_COLOR,
            'starboard_color': cls.STARBOARD_COLOR,
            'suspicious_color': cls.SUSPICIOUS_COLOR,
            'upwind_alpha': cls.UPWIND_ALPHA,
            'downwind_alpha': cls.DOWNWIND_ALPHA,
            'map_zoom': cls.MAP_ZOOM,
            'track_line_width': cls.TRACK_LINE_WIDTH,
            'segment_line_width': cls.SEGMENT_LINE_WIDTH,
        }