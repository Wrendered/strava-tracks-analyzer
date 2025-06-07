"""
Parameter control components for the analysis page.

This module contains UI components for parameter inputs and controls,
extracted from the main analysis page for better organization.
"""

import streamlit as st
import logging
from typing import Callable, Optional

from config.settings import (
    DEFAULT_ANGLE_TOLERANCE,
    DEFAULT_MIN_DURATION, 
    DEFAULT_MIN_DISTANCE,
    DEFAULT_MIN_SPEED,
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
)

logger = logging.getLogger(__name__)


def render_parameter_sidebar(on_param_change: Callable[[], None]) -> None:
    """
    Render the parameter control sidebar.
    
    Args:
        on_param_change: Callback function to trigger when parameters change
    """
    with st.sidebar:
        st.header("Track Analysis Parameters")
        
        _render_segment_detection_controls(on_param_change)
        _render_wind_angle_explanation()


def _render_segment_detection_controls(on_param_change: Callable[[], None]) -> None:
    """Render segment detection parameter controls."""
    st.subheader("Segment Detection")
    
    # Store current values to detect changes
    prev_angle_tolerance = st.session_state.get('angle_tolerance', DEFAULT_ANGLE_TOLERANCE)
    prev_min_duration = st.session_state.get('min_duration', DEFAULT_MIN_DURATION)
    prev_min_distance = st.session_state.get('min_distance', DEFAULT_MIN_DISTANCE)
    prev_min_speed = st.session_state.get('min_speed', DEFAULT_MIN_SPEED)
    
    # Main parameter - always visible
    angle_tolerance = st.slider(
        "Angle Tolerance (°)", 
        min_value=5, max_value=30, 
        value=prev_angle_tolerance,
        help="How much the bearing can vary within a segment. Lower = more precise segments.",
        key="angle_tolerance_slider"
    )
    if angle_tolerance != prev_angle_tolerance:
        st.session_state.angle_tolerance = angle_tolerance
        on_param_change()
    
    # Advanced parameters in collapsible section
    with st.expander("🔧 Advanced Parameters", expanded=False):
        st.caption("Fine-tune segment detection criteria. Default values work well for most tracks.")
        
        min_duration = st.slider(
            "Min Duration (sec)", 
            min_value=5, max_value=60, 
            value=prev_min_duration,
            help="Minimum time a segment must last to be included",
            key="min_duration_slider"
        )
        if min_duration != prev_min_duration:
            st.session_state.min_duration = min_duration
            on_param_change()
        
        min_distance = st.slider(
            "Min Distance (m)", 
            min_value=10, max_value=200, 
            value=prev_min_distance,
            help="Minimum distance a segment must cover to be included",
            key="min_distance_slider"
        )
        if min_distance != prev_min_distance:
            st.session_state.min_distance = min_distance
            on_param_change()
        
        min_speed = st.slider(
            "Min Speed (knots)", 
            min_value=5.0, max_value=20.0, 
            value=prev_min_speed, 
            step=0.5,
            help="Minimum average speed for segments to be included in analysis",
            key="min_speed_slider"
        )
        if min_speed != prev_min_speed:
            st.session_state.min_speed = min_speed
            on_param_change()
        
        st.markdown("---")
        st.caption("**Speed Filtering & Wind Analysis**")
        
        prev_active_speed_threshold = st.session_state.get('active_speed_threshold', 5.0)
        active_speed_threshold = st.slider(
            "Active Speed Threshold (knots)", 
            min_value=0.0, max_value=10.0, 
            value=prev_active_speed_threshold, 
            step=0.5,
            help="Speeds below this will be excluded from average speed calculation",
            key="active_speed_threshold_slider"
        )
        if active_speed_threshold != prev_active_speed_threshold:
            st.session_state.active_speed_threshold = active_speed_threshold
            # This one doesn't need to trigger a full segment recalculation, only metrics
        
        # Technical parameter - but important for accurate analysis
        prev_suspicious_angle_threshold = st.session_state.get('suspicious_angle_threshold', DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD)
        suspicious_angle_threshold = st.slider(
            "Minimum Sailing Angle (°)", 
            min_value=15, 
            max_value=35, 
            value=prev_suspicious_angle_threshold,
            help="Angles closer to wind than this are considered physically impossible and excluded from wind direction estimation",
            key="suspicious_angle_threshold_slider"
        )
        
        # Update the threshold in session state and trigger recalculation if changed
        if suspicious_angle_threshold != prev_suspicious_angle_threshold:
            st.session_state.suspicious_angle_threshold = suspicious_angle_threshold
            on_param_change()


def _render_wind_angle_explanation() -> None:
    """Render wind angle explanation section."""
    st.subheader("Wind Angle Explanation")
    
    st.markdown("""
    <div style="background-color: var(--secondary-background-color, #f0f2f6); color: var(--text-color, #262730); padding: 12px; border-radius: 6px; margin: 8px 0;">
        <strong>Understanding Wind Angles:</strong><br>
        <span style="font-size: 13px;">
        • <strong>30-50°</strong>: Typical upwind sailing angles<br>
        • <strong>90°+</strong>: Reaching and downwind angles<br>
        • <strong>Port/Starboard</strong>: Wind coming from left/right side<br>
        • <strong>VMG</strong>: Speed component directly toward/away from wind
        </span>
    </div>
    """, unsafe_allow_html=True)
    


def render_manual_recalc_button() -> bool:
    """
    Render manual recalculation button.
    
    Returns:
        bool: True if the button was clicked
    """
    # Only show if data is loaded
    if 'track_data' not in st.session_state or st.session_state.track_data is None:
        return False
        
    return st.button(
        "🔄 Recalculate All Segments", 
        help="Force recalculation of all segments with current parameters",
        key="manual_recalc_btn"
    )