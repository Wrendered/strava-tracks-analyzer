"""
Application settings and constants.

This module centralizes all configuration values and constants used throughout the application,
making it easier to maintain and modify application behavior.
"""

import os
import logging

# App information
APP_NAME = "WingWizard"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Analyze wingfoil tracks to improve performance"

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Default values
DEFAULT_WIND_DIRECTION = 90  # Degrees

# Analysis parameters - adjusted for better track detection with short tacks
DEFAULT_ANGLE_TOLERANCE = 25  # Degrees - increased from 20° to detect more tacks with variations
DEFAULT_MIN_DURATION = 15  # Seconds - reduced from 20s to capture shorter tacks
DEFAULT_MIN_DISTANCE = 75  # Meters - reduced from 100m for better track coverage
DEFAULT_MIN_SPEED = 8.0  # Knots - lowered from 10.0 to include more valid segments
DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD = 20  # Degrees

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