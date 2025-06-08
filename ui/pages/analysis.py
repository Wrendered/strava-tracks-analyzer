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
# Keep only needed imports - most analysis is now handled by shared service
from core.calculations import analyze_wind_angles  # Still needed for fallback wind direction update
from core.metrics_advanced import calculate_vmg_upwind  # Still needed for performance stats display
from services.track_analysis_service import analyze_track_data, get_analysis_parameters_from_session

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
    Central function to recalculate segments with current parameters using shared service.
    
    Args:
        params_changed: Optional string describing which parameters changed (for logging)
        
    Returns:
        bool: True if recalculation was successful, False otherwise
    """
    # Only proceed if we have track data
    if 'track_data' not in st.session_state or st.session_state.track_data is None:
        return False
    
    try:
        # Get parameters from session state
        params = get_analysis_parameters_from_session(st.session_state)
        wind_direction = st.session_state.get('wind_direction', DEFAULT_WIND_DIRECTION)
        filename = st.session_state.get('current_file_name', 'current_track.gpx')
        
        logger.info(f"Recalculating segments: {params_changed or 'all parameters'} changed")
        logger.info(f"Using parameters: {params}, wind_direction={wind_direction}°")
        
        # Use shared analysis service for consistent processing
        analysis_result = analyze_track_data(
            track_data=st.session_state.track_data,
            initial_wind_direction=wind_direction,
            filename=filename,
            **params  # Use exact same parameters as bulk upload
        )
        
        # Store refined wind separately for reference (don't overwrite user input)
        st.session_state.refined_wind_direction = analysis_result.refined_wind
        st.session_state.wind_confidence = analysis_result.wind_confidence
        
        # Show refinement message if significant change
        if abs(analysis_result.refined_wind - wind_direction) > 2:
            st.success(f"🎯 Wind direction refined: {wind_direction}° → {analysis_result.refined_wind:.0f}° (Confidence: {analysis_result.wind_confidence})")
        
        # Update session state with processed segments
        st.session_state.track_stretches = analysis_result.segments
        
        logger.info(f"Successfully recalculated {len(analysis_result.segments)} stretches using shared service")
        return True
        
    except Exception as e:
        logger.error(f"Error recalculating segments: {e}")
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
    
    # Skip excessive segment count message
    
    # Simple, direct analysis display
    _display_simple_analysis(track_data, current_segments, filename)


def _display_simple_analysis(track_data: pd.DataFrame, segments: pd.DataFrame, filename: str):
    """Simple, reliable analysis display with visualizations."""
    
    # Basic metrics - no redundant success message
    if not segments.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_distance = segments['distance'].sum() / 1000
            st.metric("Distance", f"{total_distance:.1f} km")
        
        with col2:
            total_duration = segments['duration'].sum() / 3600
            st.metric("Duration", f"{total_duration:.1f} hr")
        
        with col3:
            if 'avg_speed_knots' in segments.columns:
                avg_speed = segments['avg_speed_knots'].mean()
                st.metric("Avg Speed", f"{avg_speed:.1f} kn")
        
        with col4:
            if 'avg_speed_knots' in segments.columns:
                max_speed = segments['avg_speed_knots'].max()
                st.metric("Max Speed", f"{max_speed:.1f} kn")
    
    # Restore original map with color-coded segments
    st.subheader("🗺️ Track Map")
    _display_original_map(track_data, segments)
    
    # Add performance stats back
    st.subheader("📊 Performance Analysis")
    _display_performance_stats(segments)
    
    # Restore polar diagram 
    _display_polar_diagram(track_data, segments)
    
    # VMG explanation - show when info button is clicked or in expander
    if st.session_state.get('show_vmg_details', False):
        # Show directly when info button is clicked
        with st.container():
            st.markdown("### ℹ️ How VMG is calculated")
            st.markdown("""
            **VMG (Velocity Made Good) = Speed × cos(angle to wind)**
            
            **Calculation Process:**
            1. **Find best angle**: Combines segment quality (distance, speed) with closeness to wind
            2. **Select segments**: Only includes segments within 20° of the best angle
            3. **Calculate VMG**: For each selected segment: Speed × cos(angle)
            4. **Distance-weighted average**: Longer segments count more in the final VMG
            
            **Example:**
            - Best angle found: 42° (quality-weighted)
            - Includes segments: 25°-62° (within 20° range)
            - Weights by distance: 1000m segment counts 10× more than 100m segment
            
            This gives a realistic VMG based on your sustained upwind performance, not just brief moments.
            """)
            if st.button("Close", key="close_vmg_details"):
                st.session_state.show_vmg_details = False
                st.rerun()
    else:
        # Also keep the expander for users who prefer that
        with st.expander("ℹ️ How VMG is calculated"):
            st.markdown("""
            **VMG (Velocity Made Good) = Speed × cos(angle to wind)**
            
            **Calculation Process:**
            1. **Find best angle**: Combines segment quality (distance, speed) with closeness to wind
            2. **Select segments**: Only includes segments within 20° of the best angle
            3. **Calculate VMG**: For each selected segment: Speed × cos(angle)
            4. **Distance-weighted average**: Longer segments count more in the final VMG
            
            **Example:**
            - Best angle found: 42° (quality-weighted)
            - Includes segments: 25°-62° (within 20° range)
            - Weights by distance: 1000m segment counts 10× more than 100m segment
            
            This gives a realistic VMG based on your sustained upwind performance, not just brief moments.
            """)
    
    # Export button after VMG explanation
    if not segments.empty:
        from ui.components.gear_export import export_to_comparison_button
        export_to_comparison_button(segments, filename)
    
    # Wind analysis with upwind stats
    st.subheader("💨 Wind Analysis")
    _display_wind_performance(segments)
    
    # Segments table (simplified)
    st.subheader("📋 Segments")
    if not segments.empty:
        _display_segments_table(segments)


def _display_original_map(track_data: pd.DataFrame, segments: pd.DataFrame):
    """Display the original color-coded map with wind arrows."""
    try:
        from utils.visualization import display_track_map
        
        if track_data.empty or segments.empty:
            st.info("No data for map")
            return
            
        # Get wind direction from session state - use REFINED if available
        wind_direction = st.session_state.get('refined_wind_direction', 
                                             st.session_state.get('wind_direction', 90))
        
        # Need to ensure segments have the required columns for color coding
        if 'sailing_type' not in segments.columns:
            # Create sailing_type from direction and tack if available
            if 'direction' in segments.columns and 'tack' in segments.columns:
                segments = segments.copy()
                segments['sailing_type'] = segments['direction'] + ' ' + segments['tack']
        
        # Need start_idx and end_idx for the original function
        if 'start_idx' not in segments.columns:
            # Create approximate indices if missing
            segments = segments.copy()
            segments['start_idx'] = range(0, len(segments) * 10, 10)
            segments['end_idx'] = range(10, (len(segments) + 1) * 10, 10)
        
        # Need speed column (not avg_speed_knots) - ENSURE consistency
        if 'speed' not in segments.columns and 'avg_speed_knots' in segments.columns:
            segments = segments.copy()
            segments['speed'] = segments['avg_speed_knots']
        
        # Debug: Compare filtering methods
        if 'angle_to_wind' in segments.columns:
            # Method 1: What performance stats use (direction == 'upwind')
            upwind_by_direction = segments[segments.get('direction', '').str.lower() == 'upwind']
            
            # Method 2: What polar plot might use (angle < 90°) 
            upwind_by_angle = segments[segments['angle_to_wind'] < 90]
            
            if not upwind_by_direction.empty and not upwind_by_angle.empty:
                st.caption(f"Performance uses {len(upwind_by_direction)} 'upwind' segments (angles {upwind_by_direction['angle_to_wind'].min():.0f}°-{upwind_by_direction['angle_to_wind'].max():.0f}°)")
                st.caption(f"Polar plot uses {len(upwind_by_angle)} <90° segments (angles {upwind_by_angle['angle_to_wind'].min():.0f}°-{upwind_by_angle['angle_to_wind'].max():.0f}°)")
        
        # Call the original display function
        display_track_map(track_data, segments, wind_direction)
        
    except Exception as e:
        st.error(f"Map display error: {e}")


def _display_polar_diagram(track_data: pd.DataFrame, segments: pd.DataFrame):
    """Display the original polar performance diagram."""
    try:
        from utils.visualization import plot_polar_diagram
        
        if segments.empty:
            st.info("No segments for polar diagram")
            return
            
        # Need required columns for polar diagram
        required_cols = ['tack', 'angle_to_wind', 'speed', 'distance']
        missing_cols = [col for col in required_cols if col not in segments.columns]
        
        if missing_cols:
            # Try to create missing columns
            segments = segments.copy()
            
            if 'speed' not in segments.columns and 'avg_speed_knots' in segments.columns:
                segments['speed'] = segments['avg_speed_knots']
            
            if 'tack' not in segments.columns:
                st.info("Tack information not available for polar diagram")
                return
                
            if 'angle_to_wind' not in segments.columns:
                st.info("Wind angle information not available for polar diagram")
                return
        
        # Use refined wind direction if available, otherwise user's estimate
        wind_direction = st.session_state.get('refined_wind_direction',
                                             st.session_state.get('wind_direction', 90))
        
        # Create and display the polar diagram
        fig = plot_polar_diagram(segments, wind_direction)
        if fig is not None:
            st.pyplot(fig)
        else:
            st.info("Unable to generate polar diagram")
            
    except Exception as e:
        st.error(f"Polar diagram error: {e}")


def _display_performance_stats(segments: pd.DataFrame):
    """Display performance statistics including VMG."""
    try:
        if segments.empty:
            return
            
        # Calculate VMG stats (handle both uppercase and lowercase)
        upwind_segments = segments[segments.get('direction', '').str.lower() == 'upwind'] if 'direction' in segments.columns else pd.DataFrame()
        downwind_segments = segments[segments.get('direction', '').str.lower() == 'downwind'] if 'direction' in segments.columns else pd.DataFrame()
        
        # Create three columns with emphasis on VMG
        col1, col2, col3 = st.columns([2, 1.5, 1.5])
        
        with col1:
            # VMG with special styling
            st.markdown("""
            <style>
            .vmg-container {
                position: relative;
                display: inline-block;
            }
            .vmg-highlight {
                background: linear-gradient(45deg, #0068C9, #00A3FF);
                padding: 2px 8px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                margin-right: 5px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            if not upwind_segments.empty and 'avg_speed_knots' in upwind_segments.columns:
                upwind_vmg = calculate_vmg_upwind(upwind_segments)
                
                # Create two sub-columns for VMG display and info button
                vmg_col, info_col = st.columns([3, 1])
                
                with vmg_col:
                    # Custom VMG display
                    st.markdown(f"""
                    <div class="vmg-container">
                        <span class="vmg-highlight">⭐ VMG</span>
                        <span><b>{upwind_vmg:.1f} kn</b></span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption("Your effective upwind speed")
                
                with info_col:
                    # Clickable info button that toggles the calculation details
                    if st.button("ℹ️", key="vmg_info_button", help="Click to see how VMG is calculated"):
                        st.session_state.show_vmg_details = not st.session_state.get('show_vmg_details', False)
            else:
                st.metric("Upwind VMG", "N/A")
        
        with col2:
            if not upwind_segments.empty and 'angle_to_wind' in upwind_segments.columns:
                # Best upwind angle = SMALLEST angle (closest to wind)
                best_upwind_angle = upwind_segments['angle_to_wind'].min()
                st.metric("Best Upwind Angle", f"{best_upwind_angle:.0f}°")
            else:
                st.metric("Best Upwind Angle", "N/A")
        
        with col3:
            if not upwind_segments.empty and 'angle_to_wind' in upwind_segments.columns:
                # Calculate the average upwind performance (cluster average used for VMG)
                avg_upwind_angle = upwind_segments['angle_to_wind'].mean()
                st.metric("Avg Upwind Angle", f"{avg_upwind_angle:.0f}°")
            else:
                st.metric("Avg Upwind Angle", "N/A")
                
    except Exception as e:
        st.error(f"Performance stats error: {e}")


def _display_wind_performance(segments: pd.DataFrame):
    """Display wind analysis and tack performance."""
    try:
        if segments.empty:
            return
            
        wind_dir = st.session_state.get('wind_direction', 90)
        refined_wind = st.session_state.get('refined_wind_direction')
        
        # Tack analysis for upwind segments (handle both uppercase and lowercase)
        upwind = segments[segments.get('direction', '').str.lower() == 'upwind'] if 'direction' in segments.columns else pd.DataFrame()
        
        if not upwind.empty and 'tack' in upwind.columns and 'angle_to_wind' in upwind.columns:
            port_segments = upwind[upwind['tack'] == 'Port']
            starboard_segments = upwind[upwind['tack'] == 'Starboard']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Your Estimate", f"{wind_dir}°")
            
            with col2:
                if refined_wind:
                    confidence = st.session_state.get('wind_confidence', 'unknown')
                    st.metric("Refined (Used)", f"{refined_wind:.0f}°", 
                            delta=f"{refined_wind - wind_dir:+.0f}°" if abs(refined_wind - wind_dir) > 0.5 else None)
                else:
                    st.metric("Using Estimate", f"{wind_dir}°")
            
            with col3:
                if not port_segments.empty:
                    port_avg_angle = port_segments['angle_to_wind'].mean()
                    st.metric("Port Avg Angle", f"{port_avg_angle:.1f}°")
                else:
                    st.metric("Port Avg Angle", "N/A")
            
            with col4:
                if not starboard_segments.empty:
                    starboard_avg_angle = starboard_segments['angle_to_wind'].mean()
                    st.metric("Starboard Avg Angle", f"{starboard_avg_angle:.1f}°")
                else:
                    st.metric("Starboard Avg Angle", "N/A")
        else:
            st.info("No upwind segments for tack analysis")
            
    except Exception as e:
        st.error(f"Wind analysis error: {e}")


def _display_segments_table(segments: pd.DataFrame):
    """Display a clean segments table."""
    try:
        # Select key columns for display
        display_cols = ['distance', 'duration', 'avg_speed_knots', 'bearing']
        if 'sailing_type' in segments.columns:
            display_cols.insert(0, 'sailing_type')
        if 'angle_to_wind' in segments.columns:
            display_cols.append('angle_to_wind')
            
        available_cols = [col for col in display_cols if col in segments.columns]
        
        if available_cols:
            display_df = segments[available_cols].copy()
            
            # Round for clean display
            if 'distance' in display_df.columns:
                display_df['distance'] = display_df['distance'].round(0).astype(int)
            if 'duration' in display_df.columns:
                display_df['duration'] = display_df['duration'].round(0).astype(int)
            if 'avg_speed_knots' in display_df.columns:
                display_df['avg_speed_knots'] = display_df['avg_speed_knots'].round(1)
            if 'bearing' in display_df.columns:
                display_df['bearing'] = display_df['bearing'].round(0).astype(int)
            if 'angle_to_wind' in display_df.columns:
                display_df['angle_to_wind'] = display_df['angle_to_wind'].round(1)
            
            # Rename columns for better display
            column_names = {
                'sailing_type': 'Type',
                'distance': 'Distance (m)',
                'duration': 'Duration (s)', 
                'avg_speed_knots': 'Speed (kn)',
                'bearing': 'Bearing (°)',
                'angle_to_wind': 'Wind Angle (°)'
            }
            
            display_df = display_df.rename(columns=column_names)
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No segment data to display")
            
    except Exception as e:
        st.error(f"Table display error: {e}")