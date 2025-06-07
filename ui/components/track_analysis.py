"""
Track analysis and metrics display components.

This module contains UI components for displaying track analysis results,
extracted from the main analysis page for better organization.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Any, List

from core.metrics import calculate_track_metrics
from core.metrics_advanced import calculate_vmg_upwind, calculate_vmg_downwind
from ui.components.visualization import display_track_map
from ui.components.filters import segment_selection_bar, segment_details_table, segment_selection_checkboxes
from ui.components.wind_ui import reestimate_wind_button
from ui.components.gear_export import export_to_comparison_button
from utils.visualization import plot_polar_diagram

logger = logging.getLogger(__name__)


def render_track_analysis_section(
    track_data: pd.DataFrame,
    segments: pd.DataFrame,
    filename: str
) -> None:
    """
    Render the main track analysis section.
    
    Args:
        track_data: Raw GPS track data
        segments: Analyzed segments
        filename: Name of uploaded file
    """
    if track_data is None or track_data.empty:
        st.info("👆 Upload a GPX file to begin analysis")
        return
    
    # Check if we have segments
    if segments is None or segments.empty:
        st.warning("⚠️ No segments detected with current parameters. Try adjusting the angle tolerance or minimum criteria.")
        return
    
    st.success(f"✅ Analysis complete! Found **{len(segments)}** sailing segments")
    
    # Render different sections
    _render_performance_metrics(segments)
    _render_track_visualization(track_data, segments)
    _render_wind_analysis_section(segments)
    _render_detailed_analysis(segments, filename)


def _render_performance_metrics(segments: pd.DataFrame) -> None:
    """Render performance metrics section."""
    st.subheader("📊 Performance Metrics")
    
    try:
        # Calculate basic metrics
        total_distance = segments['distance'].sum() / 1000  # Convert to km
        total_duration = segments['duration'].sum() / 3600  # Convert to hours
        avg_speed = segments['avg_speed_knots'].mean() if 'avg_speed_knots' in segments.columns else 0
        max_speed = segments['avg_speed_knots'].max() if 'avg_speed_knots' in segments.columns else 0
        
        # Create metrics columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Distance", f"{total_distance:.1f} km")
        with col2:
            st.metric("Duration", f"{total_duration:.1f} hours")
        with col3:
            st.metric("Avg Speed", f"{avg_speed:.1f} knots")
        with col4:
            st.metric("Max Speed", f"{max_speed:.1f} knots")
        
        # VMG Analysis if wind analysis is available
        if 'angle_to_wind' in segments.columns:
            _render_vmg_analysis(segments)
            
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        st.error("❌ Error calculating performance metrics")


def _render_vmg_analysis(segments: pd.DataFrame) -> None:
    """Render VMG (Velocity Made Good) analysis."""
    try:
        # Separate upwind and downwind segments
        upwind_segments = segments[segments['angle_to_wind'] < 90]
        downwind_segments = segments[segments['angle_to_wind'] >= 90]
        
        # Calculate VMG if we have segments
        vmg_upwind = None
        vmg_downwind = None
        
        if not upwind_segments.empty:
            vmg_upwind = calculate_vmg_upwind(upwind_segments)
            
        if not downwind_segments.empty:
            vmg_downwind = calculate_vmg_downwind(downwind_segments)
        
        # Display VMG metrics
        if vmg_upwind is not None or vmg_downwind is not None:
            st.markdown("**VMG (Velocity Made Good)**")
            
            vmg_col1, vmg_col2 = st.columns(2)
            with vmg_col1:
                if vmg_upwind is not None:
                    st.metric("VMG Upwind", f"{vmg_upwind:.1f} knots")
                else:
                    st.metric("VMG Upwind", "No data")
            
            with vmg_col2:
                if vmg_downwind is not None:
                    st.metric("VMG Downwind", f"{vmg_downwind:.1f} knots")
                else:
                    st.metric("VMG Downwind", "No data")
                    
    except Exception as e:
        logger.error(f"Error calculating VMG: {e}")


def _render_track_visualization(track_data: pd.DataFrame, segments: pd.DataFrame) -> None:
    """Render track visualization section."""
    st.subheader("🗺️ Track Visualization")
    
    try:
        # Get wind direction from session state
        wind_direction = st.session_state.get('wind_direction', 90.0)
        estimated_wind = st.session_state.get('estimated_wind', None)
        
        # Display the map with wind direction
        display_track_map(track_data, segments, wind_direction, estimated_wind)
        
        # Add polar diagram if we have wind analysis
        if 'angle_to_wind' in segments.columns and 'tack' in segments.columns:
            st.subheader("📊 Polar Performance Diagram")
            
            # Filter segments with valid wind angles
            valid_segments = segments[
                (segments['angle_to_wind'].notna()) & 
                (segments['avg_speed_knots'].notna()) &
                (segments['avg_speed_knots'] > 0)
            ]
            
            if not valid_segments.empty:
                fig = plot_polar_diagram(valid_segments, wind_direction)
                if fig is not None:
                    st.pyplot(fig)
                else:
                    st.info("Unable to generate polar diagram with current data")
            else:
                st.info("No valid wind angle data for polar diagram")
                
    except Exception as e:
        logger.error(f"Error rendering track visualization: {e}")
        st.error("❌ Error displaying track visualization")


def _render_wind_analysis_section(segments: pd.DataFrame) -> None:
    """Render wind analysis section."""
    if 'angle_to_wind' not in segments.columns:
        return
        
    st.subheader("💨 Wind Analysis")
    
    try:
        # Get current wind direction from session state
        current_wind = st.session_state.get('wind_direction', 90.0)
        
        # Wind re-estimation button with required parameters
        def on_wind_updated(new_wind):
            """Callback for when wind direction is updated."""
            from ui.pages.analysis import update_wind_direction
            return update_wind_direction(new_wind, recalculate_stretches=True)
        
        reestimate_wind_button(segments, current_wind, on_success_callback=on_wind_updated)
        
        # Tack analysis
        if 'tack' in segments.columns:
            _render_tack_analysis(segments)
            
    except Exception as e:
        logger.error(f"Error in wind analysis section: {e}")
        st.error("❌ Error in wind analysis")


def _render_tack_analysis(segments: pd.DataFrame) -> None:
    """Render tack analysis (port vs starboard)."""
    try:
        # Filter upwind segments for tack analysis
        upwind = segments[segments['angle_to_wind'] < 90]
        
        if upwind.empty:
            st.info("No upwind segments for tack analysis")
            return
        
        # Calculate tack statistics
        port_segments = upwind[upwind['tack'] == 'Port']
        starboard_segments = upwind[upwind['tack'] == 'Starboard']
        
        if not port_segments.empty and not starboard_segments.empty:
            port_avg_angle = port_segments['angle_to_wind'].mean()
            starboard_avg_angle = starboard_segments['angle_to_wind'].mean()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Port Tack", f"{port_avg_angle:.1f}°", 
                         help=f"Average upwind angle on port tack ({len(port_segments)} segments)")
            
            with col2:
                st.metric("Starboard Tack", f"{starboard_avg_angle:.1f}°",
                         help=f"Average upwind angle on starboard tack ({len(starboard_segments)} segments)")
            
            with col3:
                angle_diff = abs(port_avg_angle - starboard_avg_angle)
                st.metric("Tack Balance", f"{angle_diff:.1f}°",
                         help="Difference between port and starboard angles (lower is better)")
        
    except Exception as e:
        logger.error(f"Error in tack analysis: {e}")


def _render_detailed_analysis(segments: pd.DataFrame, filename: str) -> None:
    """Render detailed analysis section with data tables."""
    st.subheader("📋 Detailed Analysis")
    
    try:
        # Prepare segments data with required columns for filtering
        prepared_segments = segments.copy()
        
        # Add original_index if it doesn't exist
        if 'original_index' not in prepared_segments.columns:
            prepared_segments['original_index'] = prepared_segments.index
        
        # Add required columns for the filters
        if 'upwind_downwind' not in prepared_segments.columns and 'angle_to_wind' in prepared_segments.columns:
            prepared_segments['upwind_downwind'] = prepared_segments['angle_to_wind'].apply(
                lambda x: 'Upwind' if x < 90 else 'Downwind'
            )
        
        # Add suspicious flag if it doesn't exist
        if 'suspicious' not in prepared_segments.columns and 'angle_to_wind' in prepared_segments.columns:
            prepared_segments['suspicious'] = prepared_segments['angle_to_wind'] < 20
        
        # Add segment_id for display
        if 'segment_id' not in prepared_segments.columns:
            prepared_segments['segment_id'] = range(1, len(prepared_segments) + 1)
        
        # Add display columns for the table
        if 'heading (°)' not in prepared_segments.columns and 'bearing' in prepared_segments.columns:
            prepared_segments['heading (°)'] = prepared_segments['bearing'].round(1)
        
        if 'angle off wind (°)' not in prepared_segments.columns and 'angle_to_wind' in prepared_segments.columns:
            prepared_segments['angle off wind (°)'] = prepared_segments['angle_to_wind'].round(1)
        
        if 'speed (knots)' not in prepared_segments.columns:
            if 'avg_speed_knots' in prepared_segments.columns:
                prepared_segments['speed (knots)'] = prepared_segments['avg_speed_knots'].round(1)
            elif 'speed' in prepared_segments.columns:
                prepared_segments['speed (knots)'] = prepared_segments['speed'].round(1)
        
        if 'distance (m)' not in prepared_segments.columns and 'distance' in prepared_segments.columns:
            prepared_segments['distance (m)'] = prepared_segments['distance'].round(0)
        
        if 'duration (sec)' not in prepared_segments.columns and 'duration' in prepared_segments.columns:
            prepared_segments['duration (sec)'] = prepared_segments['duration'].round(0)
        
        # Simple segment table display (replacing the complex filtering system)
        st.markdown("**Segment Summary**")
        
        # Create a simplified display table
        display_columns = ['segment_id', 'sailing_type', 'heading (°)', 'angle off wind (°)', 
                          'speed (knots)', 'distance (m)', 'duration (sec)']
        
        # Filter to only existing columns
        available_columns = [col for col in display_columns if col in prepared_segments.columns]
        
        if available_columns:
            st.dataframe(prepared_segments[available_columns], use_container_width=True, height=300)
            
            # Export option
            export_to_comparison_button(prepared_segments, filename)
        else:
            st.info("No detailed segment data available for display")
            
    except Exception as e:
        logger.error(f"Error in detailed analysis: {e}")
        st.error("❌ Error displaying detailed analysis")


def render_no_data_message() -> None:
    """Render message when no track data is available."""
    st.info("""
    👆 **Get Started:**
    1. Upload a GPX file from Strava or your GPS device
    2. Set the wind direction for your session
    3. Adjust parameters in the sidebar if needed
    4. Analyze your sailing performance!
    """)


def display_segment_count_info(segments: pd.DataFrame) -> None:
    """Display information about segment count and quality."""
    if segments is None or segments.empty:
        return
    
    segment_count = len(segments)
    
    # Determine if segment count looks reasonable
    if segment_count < 5:
        st.warning(f"⚠️ Only {segment_count} segments detected. Consider lowering the angle tolerance or minimum criteria.")
    elif segment_count > 50:
        st.info(f"ℹ️ {segment_count} segments detected. For cleaner analysis, consider raising the minimum distance or duration.")
    else:
        st.success(f"✅ {segment_count} segments detected - good for analysis!")