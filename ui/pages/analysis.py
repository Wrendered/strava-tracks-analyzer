"""
Track analysis page for the Foil Lab app.

This module contains the UI for the track analysis page.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from datetime import timedelta

# Import from core modules
from core.gpx import load_gpx_file
from core.metrics import calculate_track_metrics, calculate_average_angle_from_segments
from core.segments import find_consistent_angle_stretches, analyze_wind_angles
from core.wind.estimate import estimate_wind_direction
from core.wind.models import WindEstimate

# Import UI components
from ui.components.visualization import display_track_map, plot_polar_diagram
from ui.components.filters import segment_selection_bar, segment_details_table, segment_selection_checkboxes
from ui.components.wind_ui import wind_direction_selector, reestimate_wind_button
from ui.components.gear_export import export_to_comparison_button

# Import config settings
from config.settings import (
    DEFAULT_ANGLE_TOLERANCE,
    DEFAULT_MIN_DURATION,
    DEFAULT_MIN_DISTANCE,
    DEFAULT_MIN_SPEED,
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_WIND_DIRECTION
)

logger = logging.getLogger(__name__)

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
    
    # If we have base (non-analyzed) track data, we'll use it to regenerate stretches
    if 'track_data' in st.session_state and st.session_state.track_data is not None:
        try:
            # Get parameters from session state or use defaults
            angle_tolerance = st.session_state.get('angle_tolerance', DEFAULT_ANGLE_TOLERANCE)
            min_duration = st.session_state.get('min_duration', DEFAULT_MIN_DURATION)
            min_distance = st.session_state.get('min_distance', DEFAULT_MIN_DISTANCE)
            min_speed = st.session_state.get('min_speed', DEFAULT_MIN_SPEED)
            
            # Re-detect stretches from raw data
            base_stretches = find_consistent_angle_stretches(
                st.session_state.track_data, 
                angle_tolerance, 
                min_duration, 
                min_distance
            )
            
            # Filter by minimum speed
            min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
            if not base_stretches.empty:
                base_stretches = base_stretches[base_stretches['speed'] >= min_speed_ms]
                
                # Analyze with new wind direction
                recalculated = analyze_wind_angles(base_stretches, new_wind_direction)
                
                # Update session state
                st.session_state.track_stretches = recalculated
                logger.info(f"Successfully recalculated {len(recalculated)} stretches with wind direction {new_wind_direction}°")
                return True
        except Exception as e:
            logger.error(f"Error recalculating stretches: {e}")
            return False
    
    # Fallback: try to update existing stretches directly
    try:
        recalculated = analyze_wind_angles(st.session_state.track_stretches, new_wind_direction)
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
    
    # Sidebar parameters
    with st.sidebar:
        # Clean up sidebar by removing redundant headers
        st.header("Track Analysis Parameters")
        
        # No automatic detection anymore - all based on user input
        auto_detect_wind = False
        
        # Segment detection parameters
        st.subheader("Segment Detection")
        angle_tolerance = st.slider("Angle Tolerance (°)", 
                                   min_value=5, max_value=30, 
                                   value=st.session_state.get('angle_tolerance', DEFAULT_ANGLE_TOLERANCE),
                                   help="How much the bearing can vary within a segment")
        # Store in session state
        st.session_state.angle_tolerance = angle_tolerance
        
        # Minimum criteria
        min_duration = st.slider("Min Duration (sec)", 
                                min_value=5, max_value=60, 
                                value=st.session_state.get('min_duration', DEFAULT_MIN_DURATION))
        st.session_state.min_duration = min_duration
        
        min_distance = st.slider("Min Distance (m)", 
                                min_value=10, max_value=200, 
                                value=st.session_state.get('min_distance', DEFAULT_MIN_DISTANCE))
        st.session_state.min_distance = min_distance
        
        min_speed = st.slider("Min Speed (knots)", 
                             min_value=5.0, max_value=20.0, 
                             value=st.session_state.get('min_speed', DEFAULT_MIN_SPEED), 
                             step=0.5)
        st.session_state.min_speed = min_speed
        
        st.subheader("Speed Filter")
        active_speed_threshold = st.slider("Active Speed Threshold (knots)", 
                                          min_value=0.0, max_value=10.0, value=5.0, step=0.5,
                                          help="Speeds below this will be excluded from average speed calculation")

        min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
        
        # Technical parameter - but important for accurate analysis
        # Default to 20 degrees - below this is usually not physically possible
        suspicious_angle_threshold = st.slider(
            "Minimum Sailing Angle (°)", 
            min_value=15, 
            max_value=35, 
            value=st.session_state.get('suspicious_angle_threshold', DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD),
            help="Angles closer to wind than this are considered physically impossible and excluded from wind direction estimation (20° recommended)"
        )
        
        # Update the threshold in session state
        st.session_state.suspicious_angle_threshold = suspicious_angle_threshold
            
        # Add wind angle explanation at the bottom of the sidebar
        st.divider()
        st.subheader("Wind Angle Explanation")
        st.markdown("""
        <div style="padding: 8px; background-color: #f0f2f6; border-radius: 4px;">
            <div style="font-weight: bold; margin-bottom: 5px;">The angles shown are measured relative to the wind:</div>
            <ul style="margin-top: 0; padding-left: 20px;">
                <li><strong>0°</strong> = sailing directly into the wind (impossible)</li>
                <li><strong>45°</strong> = typical upwind angle</li>
                <li><strong>90°</strong> = sailing across the wind (beam reach)</li>
                <li><strong>180°</strong> = sailing directly downwind</li>
            </ul>
            <div style="margin-top: 8px;">
                <span style="color: #0068C9;"><strong>Tip:</strong></span> 
                Smaller angles = better upwind performance<br>
                Larger angles = better downwind speed
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # File uploader and wind direction input in the main area
    # File uploader section with initial wind direction
    uploaded_file = st.file_uploader("Upload a GPX file", type=['gpx'], key="track_analysis_uploader")
    
    # Initialize file-specific wind settings if not exists
    if 'file_wind_settings' not in st.session_state:
        st.session_state.file_wind_settings = {}
    
    # Prevent uploading new file without clearing current data first
    if 'track_data' in st.session_state and st.session_state.track_data is not None and uploaded_file is not None and uploaded_file.name != st.session_state.get('current_file_name'):
        st.warning("Please clear the current data before uploading a new file.")
        uploaded_file = None  # Reset the uploader

    # Show upload options when a file is selected but not yet processed
    if uploaded_file is not None and ('track_data' not in st.session_state or uploaded_file.name != st.session_state.get('current_file_name')):
        st.info("👉 Please set your estimated wind direction and click 'Analyze Track' to process this file. We'll use this to calculate the session's average wind direction.")
        
        # Add direction reference
        st.markdown("""
        <div style="margin-bottom: 12px; padding: 8px; background-color: #f0f2f6; border-radius: 4px; text-align: center;">
            <strong>Wind Direction Reference</strong><br>
            <span style="font-size: 13px;">Wind direction is where the wind is coming FROM</span>
            <div style="display: grid; grid-template-columns: 1fr 1fr; margin-top: 5px; gap: 4px; text-align: center;">
                <div>0° = North (↓)</div>
                <div>90° = East (←)</div>
                <div>180° = South (↑)</div>
                <div>270° = West (→)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Upload options in columns for better layout
        col1, col2 = st.columns([1, 1])
        with col1:
            # Initial wind direction input for this file
            initial_wind = st.number_input(
                "Estimated Wind Direction (°)", 
                min_value=0, 
                max_value=359, 
                value=st.session_state.get('init_wind_direction', DEFAULT_WIND_DIRECTION),
                step=5,
                help="Set your best estimate of the wind direction - we'll use this to calculate a more accurate session average"
            )
            # Store for use during processing
            st.session_state.init_wind_direction = initial_wind
            
            # Flag to track if user wants to analyze
            if 'analyze_confirmed' not in st.session_state:
                st.session_state.analyze_confirmed = False
        
        with col2:
            # Process button to analyze with the selected wind direction
            if st.button("Analyze Track", type="primary"):
                st.session_state.analyze_confirmed = True
                st.session_state.process_this_file = uploaded_file.name
                # Will be processed below only after this button is clicked
    else:
        # Reset confirmation flag when no new file is selected
        st.session_state.analyze_confirmed = False
    
    # Button to clear data - shown after a file is loaded and highlighted to encourage use before uploading new files
    if 'track_data' in st.session_state and st.session_state.track_data is not None:
        if st.button("Clear Current Data", key="clear_track_data", type="primary"):
            st.session_state.track_data = None
            st.session_state.track_metrics = None
            st.session_state.track_stretches = None
            st.session_state.track_name = None
            st.session_state.wind_direction = DEFAULT_WIND_DIRECTION
            st.session_state.estimated_wind = None
            st.session_state.current_file_name = None
            st.session_state.analyze_confirmed = False
            st.rerun()
    
    # Wind direction adjustment section - only shown after a file is loaded
    if 'track_data' in st.session_state and st.session_state.track_data is not None:
        # Display current file and wind direction info
        st.markdown(f"#### Current Track: {st.session_state.track_name}")
        
        # Use our improved wind direction UI component
        # Initialize wind direction if not already set
        if 'wind_direction' not in st.session_state:
            # This ensures first-time uploads will use the default
            st.session_state.wind_direction = DEFAULT_WIND_DIRECTION
        
        # Get current values
        current_wind = st.session_state.wind_direction
        estimated_wind = st.session_state.get('estimated_wind')
        current_file = st.session_state.get('current_file_name')
        
        # Store this file's wind settings if not already done
        if current_file and current_file not in st.session_state.file_wind_settings:
            st.session_state.file_wind_settings[current_file] = {
                'wind_direction': current_wind,
                'estimated_wind': estimated_wind
            }
        
        # Use the wind direction selector component
        def on_wind_change(new_wind_direction):
            if update_wind_direction(new_wind_direction):
                # Update this file's settings in our persistent dictionary
                if current_file:
                    if current_file not in st.session_state.file_wind_settings:
                        st.session_state.file_wind_settings[current_file] = {}
                    st.session_state.file_wind_settings[current_file]['wind_direction'] = new_wind_direction
                
                st.success(f"Wind direction updated to {new_wind_direction}°")
                st.rerun()  # Force UI refresh with new angles
        
        # Show the wind direction adjustment UI
        user_wind_direction = wind_direction_selector(
            current_wind=current_wind,
            estimated_wind=estimated_wind,
            on_change_callback=on_wind_change
        )
    
    # Process new file upload - but only if user has confirmed with Analyze button
    if uploaded_file is not None and st.session_state.get('analyze_confirmed', False) and uploaded_file.name == st.session_state.get('process_this_file'):
        logger.info(f"Processing uploaded file: {uploaded_file.name}")
        
        # Add a fancy progress bar with stages
        progress_container = st.empty()
        with progress_container.container():
            progress_bar = st.progress(0, "Preparing to analyze your track...")
            
            # Load GPX data
            try:
                progress_text = st.empty()
                progress_text.markdown("🔍 **Stage 1/5:** Reading GPX file...")
                progress_bar.progress(10)
                
                gpx_result = load_gpx_file(uploaded_file)
                
                # Handle both old and new return formats
                if isinstance(gpx_result, tuple):
                    gpx_data, metadata = gpx_result
                    track_name = metadata.get('name', 'Unknown Track')
                else:
                    gpx_data = gpx_result
                    track_name = 'Unknown Track'
                
                progress_bar.progress(30)
                progress_text.markdown("🧮 **Stage 2/5:** Calculating basic metrics...")
                
                # Store in session state
                st.session_state.track_data = gpx_data
                st.session_state.track_name = track_name
                
                progress_bar.progress(50)
                progress_text.markdown("🔬 **Stage 3/5:** Detecting sailing segments...")
                
                logger.info(f"Loaded GPX file with {len(gpx_data)} points")
                
                # Calculate basic track metrics
                metrics = calculate_track_metrics(gpx_data, min_speed_knots=active_speed_threshold)
                st.session_state.track_metrics = metrics
                
                # Create stretches
                stretches = find_consistent_angle_stretches(
                    gpx_data, angle_tolerance, min_duration, min_distance
                )
                
                # Filter stretches by speed
                if not stretches.empty:
                    min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
                    stretches = stretches[stretches['speed'] >= min_speed_ms]
                    
                # Store in session state if not empty
                if not stretches.empty:
                    st.session_state.track_stretches = stretches
                    
                    progress_bar.progress(70)
                    progress_text.markdown("💨 **Stage 4/5:** Analyzing wind patterns...")
                    
                    # Use the user-provided wind direction as starting point
                    try:
                        # Get initial wind direction from input during file upload
                        user_provided_wind = st.session_state.get('init_wind_direction', DEFAULT_WIND_DIRECTION)
                        logger.info(f"Using initial wind direction for this file: {user_provided_wind}°")
                        
                        # Store the current file name for tracking
                        st.session_state.current_file_name = uploaded_file.name
                        
                        # Use the new unified wind estimation API
                        analyzed_stretches = analyze_wind_angles(stretches.copy(), user_provided_wind)
                        
                        # Get wind estimate with confidence level
                        wind_estimate = estimate_wind_direction(
                            analyzed_stretches.copy(),
                            user_provided_wind,
                            method="iterative",
                            suspicious_angle_threshold=suspicious_angle_threshold
                        )
                        
                        # If estimation succeeded, use our central update function
                        if not wind_estimate.user_provided:
                            refined_wind = wind_estimate.direction
                            logger.info(f"Refined wind direction from user input: {refined_wind:.1f}°")
                            
                            # Store estimate for reference
                            st.session_state.estimated_wind = refined_wind
                            
                            # Use our centralized function to update wind direction and all calculations
                            update_success = update_wind_direction(refined_wind)
                            
                            if update_success:
                                # Update UI with the new wind direction
                                user_wind_direction = refined_wind
                            else:
                                logger.error("Failed to update calculations with refined wind direction")
                    except Exception as e:
                        logger.error(f"Error estimating wind direction: {e}")
                
                progress_bar.progress(90)
                progress_text.markdown("📊 **Stage 5/5:** Preparing visualization...")
                
                progress_bar.progress(100)
                progress_text.markdown("✅ **Analysis complete!** Your track is ready to explore.")
                
                # When loading completes, provide feedback about wind direction
                if 'estimated_wind' in st.session_state and st.session_state.estimated_wind is not None:
                    st.success(f"✅ File loaded successfully! Session average wind direction calculated to be {st.session_state.wind_direction:.1f}° based on your sailing patterns.")
                else:
                    st.success("✅ File loaded successfully! Now set your wind direction estimate →")
                    st.info("👉 Enter your best estimate of the wind direction from your session. This will help us analyze your performance at different sailing angles.")
            except Exception as e:
                logger.error(f"Error loading GPX file: {e}")
                st.error(f"Error loading GPX file: {e}")
                gpx_data = pd.DataFrame()
                st.session_state.track_data = None
                st.session_state.track_name = None
                
            # Clear the progress elements when done
            progress_container.empty()
    elif 'track_data' in st.session_state and st.session_state.track_data is not None:
        # Use data from session state
        gpx_data = st.session_state.track_data
        track_name = st.session_state.track_name
        
        # Show a nicely styled info message
        st.markdown(f"""
        <div style="background-color: rgba(0, 104, 201, 0.1); padding: 10px; border-radius: 5px; border-left: 5px solid #0068C9; margin-bottom: 1rem;">
            <div style="display: flex; align-items: center;">
                <div style="font-size: 1.5rem; margin-right: 10px;">📋</div>
                <div>
                    <strong>Using previously loaded data:</strong> {track_name}<br>
                    <span style="font-size: 0.9rem;">Use "Clear Current Data" button above to upload a different file.</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # No need for additional info message as the blue box already provides guidance
    else:
        # Clear any remaining file in the uploader
        if uploaded_file is not None:
            uploaded_file = None
        gpx_data = pd.DataFrame()
    
    # Display track analysis if we have data
    if 'track_data' in st.session_state and st.session_state.track_data is not None:
        # Get current values from session state
        gpx_data = st.session_state.track_data
        metrics = st.session_state.track_metrics if 'track_metrics' in st.session_state else None
        track_name = st.session_state.track_name
        wind_direction = st.session_state.get('wind_direction', DEFAULT_WIND_DIRECTION)
        estimated_wind = st.session_state.get('estimated_wind')
        stretches = st.session_state.track_stretches if 'track_stretches' in st.session_state else None
        
        # Display track summary in a nice card-like container
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown("### 📌 Track Overview")
        
        # Add export to comparison option - always displayed
        if metrics:
            with cols[1]:
                st.markdown("**🔄 Export to Comparison**", help="Export this track's data to the Gear Comparison page")
            
            # Save the angle results in session state for export
            angle_results = calculate_average_angle_from_segments(stretches)
            st.session_state.angle_results = angle_results
            
            # Show export form directly without requiring an initial button click
            export_id = export_to_comparison_button(metrics, stretches)
        
        with st.container(border=True):
            # Create a modern track summary layout
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            with col1:
                st.markdown(f"**🏄 {track_name}**")
                date_value = metrics.get('date', 'Unknown') if metrics else 'Unknown'
                st.markdown(f"📅 **Date:** {date_value}")
                
            with col2:
                # Duration metrics
                if metrics and 'duration' in metrics:
                    total_duration_mins = metrics['duration'].total_seconds() / 60
                    st.markdown("⏱️ **Duration**")
                    
                    if 'active_duration' in metrics:
                        active_mins = metrics['active_duration'].total_seconds() / 60
                        active_percent = (metrics['active_duration'].total_seconds() / metrics['total_duration_seconds']) * 100 if metrics['total_duration_seconds'] > 0 else 0
                        st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{total_duration_mins:.0f} min</span><br/>" + 
                                  f"<span style='font-size:0.85rem; color:var(--text-color, #666);'>Active: {active_mins:.0f} min ({active_percent:.0f}%)</span>", 
                                  unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{total_duration_mins:.0f} min</span>", 
                                  unsafe_allow_html=True)
            
            with col3:
                # Distance metrics
                if metrics and 'distance' in metrics:
                    st.markdown("📏 **Distance**")
                    st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{metrics['distance']:.2f} km</span>", 
                              unsafe_allow_html=True)
                
            with col4:
                # Speed metrics
                if metrics and 'weighted_avg_speed' in metrics:
                    st.markdown("⚡ **Average Speed**")
                    st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{metrics['weighted_avg_speed']:.1f} kn</span><br/>" + 
                              f"<span style='font-size:0.85rem; color:var(--text-color, #666);'>Above {active_speed_threshold} knots</span>", 
                              unsafe_allow_html=True)
                    
                    # Show comparison if different
                    if 'overall_avg_speed' in metrics and abs(metrics['overall_avg_speed'] - metrics['weighted_avg_speed']) > 0.1:
                        st.caption(f"Overall avg: {metrics['overall_avg_speed']:.1f} knots (with stops)")
                elif metrics and 'avg_speed' in metrics:
                    st.markdown("⚡ **Average Speed**")
                    st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{metrics['avg_speed']:.1f} kn</span>", 
                              unsafe_allow_html=True)
        
        # Continue with the rest of the analysis if we have stretches
        if stretches is not None and not stretches.empty:
            # Process stretches for display
            display_df = stretches.copy()
            display_df['original_index'] = display_df.index
            display_df = display_df.reset_index()
            display_df['suspicious'] = display_df['angle_to_wind'] < suspicious_angle_threshold
            
            # Rename columns for display
            display_df = display_df.rename(columns={
                'index': 'segment_id',
                'bearing': 'heading (°)',
                'angle_to_wind': 'angle off wind (°)',
                'distance': 'distance (m)',
                'speed': 'speed (knots)',
                'duration': 'duration (sec)'
            })
            
            # Format for display
            for col in ['heading (°)', 'angle off wind (°)']:
                display_df[col] = display_df[col].round(1)
            display_df['distance (m)'] = display_df['distance (m)'].round(1)
            display_df['speed (knots)'] = display_df['speed (knots)'].round(2)
            
            # SEGMENT SELECTION BAR - Placed before the map
            st.markdown("### 🔍 Segment Selection")
            
            # Get selected segments
            selected_segments, filter_states = segment_selection_bar(display_df, suspicious_angle_threshold)
            st.session_state.selected_segments = selected_segments
            
            # Display the map
            st.subheader("Track Map")
            display_track_map(gpx_data, stretches, wind_direction, estimated_wind)
            
            # Reorganize for a more compact, dense layout with 2 columns for main content
            col1, col2 = st.columns([1, 1])
            
            # LEFT COLUMN - Performance Analysis 
            with col1:
                # PERFORMANCE ANALYSIS - Best Angles Section
                st.subheader("📊 Performance Analysis")
                
                # Get the filtered segments for analysis
                if selected_segments and len(selected_segments) > 0:
                    analysis_stretches = stretches.loc[stretches.index.isin(selected_segments)]
                else:
                    analysis_stretches = stretches
                
                # Find the best angles and speeds
                if not analysis_stretches.empty:
                    # Split into upwind/downwind for analysis
                    upwind = analysis_stretches[analysis_stretches['angle_to_wind'] < 90]
                    downwind = analysis_stretches[analysis_stretches['angle_to_wind'] >= 90]
                    
                    with st.container(border=True):
                        best_cols = st.columns(2)
                        
                        # UPWIND PERFORMANCE - Best angles/speeds - SIMPLIFIED
                        with best_cols[0]:
                            st.markdown("#### 🔼 Best Upwind")
                            if not upwind.empty:
                                # Split by tack
                                port_upwind = upwind[upwind['tack'] == 'Port']
                                starboard_upwind = upwind[upwind['tack'] == 'Starboard']
                                
                                # Find best port tack upwind angle - just use minimum angle
                                if not port_upwind.empty and len(port_upwind) > 0:
                                    best_port = port_upwind.loc[port_upwind['angle_to_wind'].idxmin()]
                                    st.metric("Best Port Angle", f"{best_port['angle_to_wind']:.1f}°", 
                                            f"{best_port['speed']:.1f} knots")
                                    st.caption(f"Bearing: {best_port['bearing']:.0f}°")
                                
                                # Find best starboard tack upwind angle - just use minimum angle
                                if not starboard_upwind.empty and len(starboard_upwind) > 0:
                                    best_starboard = starboard_upwind.loc[starboard_upwind['angle_to_wind'].idxmin()]
                                    st.metric("Best Starboard Angle", f"{best_starboard['angle_to_wind']:.1f}°", 
                                            f"{best_starboard['speed']:.1f} knots")
                                    st.caption(f"Bearing: {best_starboard['bearing']:.0f}°")
                                
                                # Calculate upwind progress speed when we have both tacks
                                if 'best_port' in locals() and 'best_starboard' in locals():
                                    import math
                                    
                                    # Simply average the angles - no balancing or weighting
                                    pointing_power = (best_port['angle_to_wind'] + best_starboard['angle_to_wind']) / 2
                                    
                                    # Average speed
                                    avg_upwind_speed = (best_port['speed'] + best_starboard['speed']) / 2
                                    
                                    # Calculate upwind progress speed
                                    upwind_progress_speed = avg_upwind_speed * math.cos(math.radians(pointing_power))
                                    
                                    # Display upwind progress speed 
                                    st.metric("Upwind Progress", 
                                            f"{upwind_progress_speed:.1f} knots", 
                                            help="Effective speed directly upwind (speed × cos(angle))")
                                    
                                    # Display session average wind direction - simple average
                                    # Note the angle difference but don't balance
                                    angle_diff = abs(best_port['angle_to_wind'] - best_starboard['angle_to_wind'])
                                    st.markdown("---")
                                    st.info(f"**Session Average Wind Direction**  \n"
                                          f"Combined angle: {pointing_power:.1f}°  \n"
                                          f"(Port/Starboard difference: {angle_diff:.1f}°)")
                            else:
                                st.info("No upwind data")
                        
                        # DOWNWIND PERFORMANCE - Best angles/speeds
                        with best_cols[1]:
                            st.markdown("#### 🔽 Best Downwind")
                            if not downwind.empty:
                                # Split by tack
                                port_downwind = downwind[downwind['tack'] == 'Port']
                                starboard_downwind = downwind[downwind['tack'] == 'Starboard']
                                
                                # Find best port tack downwind angle
                                if not port_downwind.empty:
                                    # For downwind, we want the largest angle from wind
                                    best_port = port_downwind.loc[port_downwind['angle_to_wind'].idxmax()]
                                    st.metric("Best Port Angle", f"{best_port['angle_to_wind']:.1f}°",
                                            f"{best_port['speed']:.1f} knots")
                                    st.caption(f"Bearing: {best_port['bearing']:.0f}°")
                                
                                # Find best starboard tack downwind angle
                                if not starboard_downwind.empty:
                                    best_starboard = starboard_downwind.loc[starboard_downwind['angle_to_wind'].idxmax()]
                                    st.metric("Best Starboard Angle", f"{best_starboard['angle_to_wind']:.1f}°",
                                            f"{best_starboard['speed']:.1f} knots")
                                    st.caption(f"Bearing: {best_starboard['bearing']:.0f}°")
                            else:
                                st.info("No downwind data")
            
            # RIGHT COLUMN - Visualizations
            with col2:
                # POLAR DIAGRAM - Visual representation of performance
                st.subheader("🎯 Sailing Performance")
                
                # Get the filtered stretches for visualization
                if selected_segments and len(selected_segments) > 0:
                    filtered_stretches = stretches.loc[stretches.index.isin(selected_segments)]
                    source_note = f"(using {len(filtered_stretches)} selected segments)"
                else:
                    filtered_stretches = stretches
                    source_note = f"(using all {len(stretches)} segments)"
                
                if len(filtered_stretches) > 2:
                    fig = plot_polar_diagram(filtered_stretches, wind_direction)
                    st.pyplot(fig)
                else:
                    st.info("Not enough data for polar plot (need at least 3 segments)")
            
            # Create tabs for segment data
            tab1, tab2 = st.tabs(["🔍 Segment Data", "📋 Advanced Selection"])
            
            with tab1:
                # Display segment data table
                segment_details_table(display_df, selected_segments)
            
            with tab2:
                # Advanced segment selection with checkboxes
                segment_selection_checkboxes(display_df)
            
            # Add wind re-estimation button and average angles at the bottom after all tabs
            if selected_segments and len(selected_segments) > 0:
                filtered_stretches = stretches.loc[stretches.index.isin(selected_segments)]
            else:
                filtered_stretches = stretches
            
            if len(filtered_stretches) > 0:
                # Add wind re-estimation button
                st.subheader("🧭 Wind Analysis Based on Selected Segments")
                
                cols = st.columns([3, 1])
                with cols[0]:
                    st.info("Use specific segments to refine the wind direction estimate")
                    st.markdown("""
                    <div style="font-size:0.9em; color: #555;">
                        <span style="color: #0068C9;">ℹ️</span> You can select specific segments in the <strong>Advanced Selection</strong> tab 
                        below to focus the analysis on your best tacks only. The calculation balances port and starboard tacks 
                        and excludes suspicious angles (< 20°).
                    </div>
                    """, unsafe_allow_html=True)
                
                with cols[1]:
                    # Add re-analyze wind button using our reusable component
                    reestimate_wind_button(
                        stretches=filtered_stretches,
                        current_wind=wind_direction,
                        suspicious_angle_threshold=suspicious_angle_threshold,
                        on_success_callback=update_wind_direction
                    )
                
                # Show average angles
                angle_results = calculate_average_angle_from_segments(filtered_stretches)
                
                with st.expander("Average Angles Details", expanded=False):
                    if angle_results['average_angle'] is not None:
                        avg_cols = st.columns(3)
                        with avg_cols[0]:
                            st.metric("Avg Angle", f"{angle_results['average_angle']:.1f}°")
                        with avg_cols[1]:
                            if angle_results['port_count'] > 0:
                                st.metric("Port Tack", f"{angle_results['port_average']:.1f}°", f"{angle_results['port_count']} segments")
                        with avg_cols[2]:
                            if angle_results['starboard_count'] > 0:
                                st.metric("Starboard Tack", f"{angle_results['starboard_average']:.1f}°", f"{angle_results['starboard_count']} segments")
        else:
            st.warning("No segments meet minimum speed criteria. Try adjusting the speed and angle parameters.")
    else:
        # Display a more helpful instruction message
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px; margin-top: 30px;">
            <h3>📤 Upload a GPX Track File</h3>
            <p>Select a GPX file from your Strava downloads or other GPS device to analyze your wingfoil session.</p>
            <p style="font-size: 0.9rem; color: #666;">The analysis will show you wind angles, speed patterns, and performance metrics for your session.</p>
        </div>
        """, unsafe_allow_html=True)