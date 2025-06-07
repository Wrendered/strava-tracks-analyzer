"""
Track analysis page for the Foil Lab app.

This module contains the UI for the track analysis page.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from datetime import timedelta
import math

# Import from core modules
from core.gpx import load_gpx_file
from core.metrics import calculate_track_metrics, calculate_average_angle_from_segments
# Import segment detection from segments package, wind analysis from calculations
from core.segments import find_consistent_angle_stretches
from core.calculations import analyze_wind_angles
from core.wind.estimate import estimate_wind_direction
from core.wind.models import WindEstimate
from core.metrics_advanced import (
    calculate_vmg_upwind,
    calculate_vmg_downwind,
    estimate_wind_direction_weighted
)
from core.wind.algorithms import estimate_wind_direction_iterative

# Import UI components
from ui.components.visualization import display_track_map, plot_polar_diagram
from ui.components.filters import segment_selection_bar, segment_details_table, segment_selection_checkboxes
from ui.components.wind_ui import wind_direction_selector, reestimate_wind_button
from ui.components.gear_export import export_to_comparison_button
from ui.components.parameter_controls import render_parameter_sidebar, render_manual_recalc_button
from ui.components.file_upload import render_file_upload_section, get_current_file_info
from ui.components.track_analysis import render_track_analysis_section, render_no_data_message, display_segment_count_info

# Import utilities
from utils.parameter_scaling import SegmentationParams

# Import config settings
from config.settings import (
    DEFAULT_ANGLE_TOLERANCE,
    DEFAULT_MIN_DURATION,
    DEFAULT_MIN_DISTANCE,
    DEFAULT_MIN_SPEED,
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_WIND_DIRECTION
)

# Advanced algorithm configuration
DEFAULT_MIN_SEGMENT_DISTANCE = 50  # Minimum segment distance for algorithms in meters
DEFAULT_VMG_ANGLE_RANGE = 20       # Range around best angle to include for VMG calculation

logger = logging.getLogger(__name__)

def recalculate_segments(params_changed=None):
    """
    Central function to recalculate segments with current parameters.
    
    Args:
        params_changed: Optional string describing which parameters changed (for logging)
        
    Returns:
        bool: True if recalculation was successful, False otherwise
    """
    # Only proceed if we have track data
    if 'track_data' not in st.session_state or st.session_state.track_data is None:
        return False
    
    try:
        # Get parameters from session state or use defaults
        angle_tolerance = st.session_state.get('angle_tolerance', DEFAULT_ANGLE_TOLERANCE)
        min_duration = st.session_state.get('min_duration', DEFAULT_MIN_DURATION)
        min_distance = st.session_state.get('min_distance', DEFAULT_MIN_DISTANCE)
        min_speed = st.session_state.get('min_speed', DEFAULT_MIN_SPEED)
        wind_direction = st.session_state.get('wind_direction', DEFAULT_WIND_DIRECTION)
        
        logger.info(f"Recalculating segments: {params_changed or 'all parameters'} changed")
        logger.info(f"Using parameters: angle_tolerance={angle_tolerance}°, min_duration={min_duration}s, "
                   f"min_distance={min_distance}m, min_speed={min_speed}kn, wind_direction={wind_direction}°")
        
        # Re-detect stretches from raw data
        base_stretches = find_consistent_angle_stretches(
            st.session_state.track_data, 
            angle_tolerance, 
            min_duration, 
            min_distance
        )
        
        # Filter by minimum speed
        if not base_stretches.empty:
            logger.info(f"Filtering {len(base_stretches)} stretches by min_speed: {min_speed} knots")
            
            # Filter by speed in knots directly - stretches['avg_speed_knots'] is already in knots
            base_stretches = base_stretches[base_stretches['avg_speed_knots'] >= min_speed]
            logger.info(f"After filtering: {len(base_stretches)} stretches remain")
            
            # Analyze with current wind direction
            recalculated = analyze_wind_angles(base_stretches, wind_direction)
            
            # Add sailing_type column for visualization
            if 'direction' in recalculated.columns and 'tack' in recalculated.columns:
                recalculated['sailing_type'] = recalculated['direction'] + ' ' + recalculated['tack']
            
            # Update session state
            st.session_state.track_stretches = recalculated
            
            # Success - no need for broken quality analysis
            
            logger.info(f"Successfully recalculated {len(recalculated)} stretches")
            return True
    except Exception as e:
        logger.error(f"Error recalculating segments: {e}")
        return False
    
    return False

def update_wind_direction(new_wind_direction, recalculate_stretches=True):
    """
    Central function to update wind direction and all related calculations.
    
    Args:
        new_wind_direction: The new wind direction to set
        recalculate_stretches: Whether to recalculate stretches with the new wind direction
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    # Store the previous wind direction for logging
    prev_wind = st.session_state.get('wind_direction', None)
    
    # Update the wind direction in session state
    st.session_state.wind_direction = new_wind_direction
    
    # Log the change
    if prev_wind is not None and prev_wind != new_wind_direction:
        logger.info(f"Wind direction updated: {prev_wind}° → {new_wind_direction}°")
    else:
        logger.info(f"Wind direction set to: {new_wind_direction}°")
    
    # If we don't need to recalculate stretches (e.g., no data loaded yet), we're done
    if not recalculate_stretches or 'track_stretches' not in st.session_state or st.session_state.track_stretches is None:
        return True
    
    # If we have base (non-analyzed) track data, use the recalculate_segments function
    if 'track_data' in st.session_state and st.session_state.track_data is not None:
        return recalculate_segments("wind direction")
    
    # Fallback: try to update existing stretches directly
    try:
        recalculated = analyze_wind_angles(st.session_state.track_stretches, new_wind_direction)
        
        # Add sailing_type column for visualization
        if 'direction' in recalculated.columns and 'tack' in recalculated.columns:
            recalculated['sailing_type'] = recalculated['direction'] + ' ' + recalculated['tack']
        
        st.session_state.track_stretches = recalculated
        logger.info(f"Updated existing stretches with wind direction {new_wind_direction}°")
        return True
    except Exception as e:
        logger.error(f"Error updating existing stretches: {e}")
        return False

def display_page():
    """Display the track analysis page."""
    st.header("Track Analysis")
    st.markdown("""
    <div style="margin-bottom: 1rem;">
        <p style="margin: 0; font-size: 1.1rem; color: var(--text-color, #555);">
        Transform your Strava tracks into actionable insights. Analyze wind angles, 
        speed, and sailing patterns to improve your wingfoiling performance.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Helper function for parameter changes
    def on_param_change():
        """Handle parameter changes by recalculating segments."""
        if 'track_data' in st.session_state and st.session_state.track_data is not None:
            recalculate_segments("segment parameters")
            st.rerun()
    
    def on_file_loaded(track_data: pd.DataFrame, filename: str):
        """Handle new file upload."""
        logger.info(f"File loaded: {filename} with {len(track_data)} points")
        # Trigger initial segment calculation
        recalculate_segments("newly loaded")
        st.rerun()
    
    def on_wind_change(wind_direction: float):
        """Handle wind direction changes."""
        update_wind_direction(wind_direction, recalculate_stretches=True)
        st.rerun()
    
    # Render sidebar parameters
    render_parameter_sidebar(on_param_change)
    
    # Convert knots to m/s for calculations
    min_speed_ms = st.session_state.get('min_speed', DEFAULT_MIN_SPEED) * 0.514444
    
    # Manual recalculation button
    if render_manual_recalc_button():
        recalculate_segments("manual recalculation")
        st.rerun()
    
    # File upload and wind direction input
    render_file_upload_section(on_file_loaded, on_wind_change)
    
    # Get current track data and segments
    file_info = get_current_file_info()
    current_segments = st.session_state.get('track_stretches')
    
    if file_info is None:
        render_no_data_message()
        return
    
    track_data, filename = file_info
    
    # Check if we have processed segments
    if current_segments is None or current_segments.empty:
        st.warning("⚠️ No segments detected. Try adjusting parameters in the sidebar.")
        return
    
    # Display segment count information
    display_segment_count_info(current_segments)
    
    # Render main track analysis
    render_track_analysis_section(track_data, current_segments, filename)