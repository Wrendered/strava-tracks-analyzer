"""
File upload and initial configuration components.

This module contains UI components for file upload and initial track configuration,
extracted from the main analysis page for better organization.
"""

import streamlit as st
import pandas as pd
import logging
from typing import Optional, Tuple, Callable

from core.gpx import load_gpx_file
from core.validation import ValidationError
from config.settings import DEFAULT_WIND_DIRECTION

logger = logging.getLogger(__name__)


def render_file_upload_section(
    on_file_loaded: Callable[[pd.DataFrame, str], None],
    on_wind_change: Callable[[float], None]
) -> None:
    """
    Render file upload section with wind direction input.
    
    Args:
        on_file_loaded: Callback when file is successfully loaded
        on_wind_change: Callback when wind direction changes
    """
    # Create two columns for file upload and wind direction
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _render_file_uploader(on_file_loaded)
    
    with col2:
        _render_wind_direction_input(on_wind_change)


def _render_file_uploader(on_file_loaded: Callable[[pd.DataFrame, str], None]) -> None:
    """Render the GPX file uploader."""
    uploaded_file = st.file_uploader(
        "Upload GPX File", 
        type=['gpx'], 
        help="Upload a GPX file from Strava or other GPS tracking apps"
    )
    
    if uploaded_file is not None:
        try:
            # Load the GPX file
            with st.spinner("Loading GPX file..."):
                result = load_gpx_file(uploaded_file)
                
                if isinstance(result, tuple):
                    track_data, metadata = result
                    # Extract filename from metadata or use uploaded filename
                    filename = metadata.get('name', uploaded_file.name)
                    if not filename:
                        filename = uploaded_file.name
                    
                    # Clean filename for session state keys (remove special characters)
                    clean_filename = "".join(c for c in str(filename) if c.isalnum() or c in (' ', '-', '_')).strip()
                else:
                    track_data = result
                    filename = uploaded_file.name
                    metadata = {}
                    clean_filename = "".join(c for c in str(filename) if c.isalnum() or c in (' ', '-', '_')).strip()
                
                if track_data is not None and not track_data.empty:
                    # Store in session state
                    st.session_state.track_data = track_data
                    st.session_state.uploaded_filename = filename
                    
                    # Initialize file-specific wind settings if not exists
                    if f'wind_direction_{clean_filename}' not in st.session_state:
                        st.session_state[f'wind_direction_{clean_filename}'] = DEFAULT_WIND_DIRECTION
                    
                    # Set current wind direction from file-specific storage
                    current_wind = st.session_state.get(f'wind_direction_{clean_filename}', DEFAULT_WIND_DIRECTION)
                    st.session_state.wind_direction = current_wind
                    
                    st.success(f"✅ Loaded {len(track_data)} GPS points from {filename}")
                    
                    # Display basic track info  
                    _display_track_summary(track_data, filename, metadata)
                    
                    # Trigger callback
                    on_file_loaded(track_data, filename)
                    
                else:
                    st.error("❌ Failed to load GPX file. Please check the file format.")
                    
        except ValidationError as e:
            logger.warning(f"Validation error loading GPX file: {e}")
            st.error(f"❌ Invalid file: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading GPX file: {e}")
            st.error(f"❌ Error loading file: {str(e)}")


def _render_wind_direction_input(on_wind_change: Callable[[float], None]) -> None:
    """Render wind direction input controls."""
    st.subheader("Wind Direction")
    
    # Get current wind direction
    current_wind = st.session_state.get('wind_direction', DEFAULT_WIND_DIRECTION)
    
    # Wind direction input
    wind_direction = st.number_input(
        "Wind Direction (°)",
        min_value=0,
        max_value=359,
        value=int(current_wind),
        step=5,
        help="Direction wind is coming FROM (0°=North, 90°=East, 180°=South, 270°=West)",
        key="wind_direction_input"
    )
    
    # Update wind direction if changed
    if wind_direction != current_wind:
        st.session_state.wind_direction = float(wind_direction)
        
        # Store file-specific wind direction if we have a file
        if 'uploaded_filename' in st.session_state:
            filename = st.session_state.uploaded_filename
            clean_filename = "".join(c for c in str(filename) if c.isalnum() or c in (' ', '-', '_')).strip()
            st.session_state[f'wind_direction_{clean_filename}'] = float(wind_direction)
        
        on_wind_change(float(wind_direction))
    
    # Wind direction reference
    st.markdown("""
    <div style="font-size: 12px; color: var(--text-color, #666); margin-top: 5px;">
        <strong>Reference:</strong> 0°=N, 90°=E, 180°=S, 270°=W
    </div>
    """, unsafe_allow_html=True)


def _display_track_summary(track_data: pd.DataFrame, filename: str, metadata: dict = None) -> None:
    """Display basic track information."""
    try:
        # Calculate basic statistics
        duration = None
        if 'time' in track_data.columns and len(track_data) > 1:
            duration = track_data['time'].max() - track_data['time'].min()
        
        # Display in a nice info box
        info_parts = [f"**{len(track_data)}** GPS points"]
        
        if duration:
            hours = duration.total_seconds() / 3600
            if hours >= 1:
                info_parts.append(f"**{hours:.1f}** hours")
            else:
                minutes = duration.total_seconds() / 60
                info_parts.append(f"**{minutes:.0f}** minutes")
        
        if 'speed' in track_data.columns:
            max_speed = track_data['speed'].max() * 1.94384  # Convert m/s to knots
            avg_speed = track_data['speed'].mean() * 1.94384
            info_parts.append(f"Max speed **{max_speed:.1f}** knots")
            info_parts.append(f"Avg speed **{avg_speed:.1f}** knots")
        
        info_text = " • ".join(info_parts)
        
        st.markdown(f"""
        <div style="background-color: var(--secondary-background-color, #f0f8ff); color: var(--text-color, #333); 
                    padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #4CAF50;">
            📊 <strong>{filename}</strong><br>
            <span style="font-size: 14px;">{info_text}</span>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        logger.warning(f"Error displaying track summary: {e}")


def get_current_file_info() -> Optional[Tuple[pd.DataFrame, str]]:
    """
    Get currently loaded file information.
    
    Returns:
        Tuple of (track_data, filename) if file is loaded, None otherwise
    """
    if ('track_data' in st.session_state and 
        st.session_state.track_data is not None and
        'uploaded_filename' in st.session_state):
        return st.session_state.track_data, st.session_state.uploaded_filename
    return None