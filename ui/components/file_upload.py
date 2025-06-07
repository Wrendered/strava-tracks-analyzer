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
    # WIND DIRECTION FIRST - Most important for accurate analysis
    st.markdown("### 🧭 Step 1: Initial Wind Estimate")
    st.info("📍 Enter your best guess - the algorithm will refine this automatically")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        _render_wind_direction_input(on_wind_change)
    with col2:
        st.markdown("**0°=North, 90°=East, 180°=South, 270°=West**")
    
    st.markdown("### 📁 Step 2: Upload Your Track")
    
    # File upload and clear button
    col1, col2 = st.columns([3, 1])
    
    with col1:
        _render_file_uploader(on_file_loaded)
    
    with col2:
        _render_clear_file_button()


def _render_file_uploader(on_file_loaded: Callable[[pd.DataFrame, str], None]) -> None:
    """Render the GPX file uploader."""
    # Show current file status if loaded
    if 'uploaded_filename' in st.session_state and st.session_state.get('track_data') is not None:
        st.info(f"📁 Current file: **{st.session_state.uploaded_filename}**")
    
    uploaded_file = st.file_uploader(
        "Upload GPX File", 
        type=['gpx'], 
        help="Upload a GPX file from Strava or other GPS tracking apps",
        key="file_uploader"
    )
    
    # Check if clear was requested
    if st.session_state.get('clear_requested', False):
        # If no file is uploaded anymore, clear completed successfully
        if uploaded_file is None:
            del st.session_state['clear_requested']
            st.success("✅ Cleared! You can now upload a new file.")
            return
        else:
            # Still has file, show warning
            st.warning("⚠️ Please click the 'X' on the file upload widget above to complete clearing")
            return
        
    if uploaded_file is not None:
        # Check if this file has already been processed to prevent infinite loops
        current_file_name = uploaded_file.name
        last_processed_file = st.session_state.get('last_processed_file')
        
        if current_file_name == last_processed_file:
            # File already processed, just display the summary
            if 'track_data' in st.session_state and 'uploaded_filename' in st.session_state:
                track_data = st.session_state.track_data
                filename = st.session_state.uploaded_filename
                # Just show minimal info, no redundant summary
                pass
            return
        
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
                    
                    # DON'T override the user's wind direction input!
                    # The user has already set it in Step 1 before uploading
                    # Just store file-specific wind if needed for later
                    if f'wind_direction_{clean_filename}' not in st.session_state:
                        # Use current wind direction if user has set it, otherwise default
                        current_wind = st.session_state.get('wind_direction', DEFAULT_WIND_DIRECTION)
                        st.session_state[f'wind_direction_{clean_filename}'] = current_wind
                    
                    # Minimal file loaded message
                    st.success(f"✅ {filename}")
                    
                    # Mark this file as processed to prevent infinite loops
                    st.session_state['last_processed_file'] = current_file_name
                    
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
    
    # Initialize wind_direction in session state if not present
    if 'wind_direction' not in st.session_state:
        st.session_state.wind_direction = DEFAULT_WIND_DIRECTION
    
    # Wind direction input - directly update session state
    wind_direction = st.number_input(
        "Wind Direction (°)",
        min_value=0,
        max_value=359,
        value=int(st.session_state.wind_direction),
        step=5,
        help="Direction wind is coming FROM",
        key="wind_input",
        on_change=lambda: _handle_wind_change(on_wind_change)
    )
    

def _handle_wind_change(on_wind_change: Callable[[float], None]) -> None:
    """Handle wind direction changes from the input widget."""
    new_wind = st.session_state.wind_input
    st.session_state.wind_direction = float(new_wind)
    
    # Store file-specific wind direction if we have a file
    if 'uploaded_filename' in st.session_state:
        filename = st.session_state.uploaded_filename
        clean_filename = "".join(c for c in str(filename) if c.isalnum() or c in (' ', '-', '_')).strip()
        st.session_state[f'wind_direction_{clean_filename}'] = float(new_wind)
    
    on_wind_change(float(new_wind))
    
    # Remove redundant reference text


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


def _render_clear_file_button() -> None:
    """Render button to clear current file."""
    if 'track_data' in st.session_state and st.session_state.track_data is not None:
        st.write("")  # Add some spacing
        if st.button("🗑️ Clear", help="Clear current file to upload a new one"):
            # Clear all related session state
            keys_to_clear = [
                'track_data', 'uploaded_filename', 'track_stretches',
                'last_processed_file', 'refined_wind_direction', 'wind_confidence'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # IMPORTANT: Set a flag to ignore the current file
            st.session_state['clear_requested'] = True
            st.rerun()


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