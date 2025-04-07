import streamlit as st
import pandas as pd
import numpy as np
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'app.log'))
    ]
)
logger = logging.getLogger(__name__)

from utils.gpx_parser import load_gpx_file
from utils.calculations import calculate_track_metrics
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles, estimate_wind_direction
from utils.visualization import display_track_map, plot_bearing_distribution, plot_polar_diagram

def main():
    st.set_page_config(
        layout="wide", 
        page_title="Strava Tracks Analyzer",
        page_icon="🪂",
        initial_sidebar_state="expanded",
        menu_items={
            'About': "Strava Tracks Analyzer - Analyze your wingfoil tracks to improve performance"
        }
    )
    
    # Main title for the app
    st.title("Strava Tracks Analyzer")
    
    # Initialize session state for navigation and data persistence
    if 'page' not in st.session_state:
        st.session_state.page = "Track Analysis"
        
    # Initialize data storage in session state if not already present
    if 'track_data' not in st.session_state:
        st.session_state.track_data = None
        
    if 'track_metrics' not in st.session_state:
        st.session_state.track_metrics = None
        
    if 'track_stretches' not in st.session_state:
        st.session_state.track_stretches = None
        
    if 'track_name' not in st.session_state:
        st.session_state.track_name = None
        
    if 'wind_direction' not in st.session_state:
        st.session_state.wind_direction = 90
        
    if 'estimated_wind' not in st.session_state:
        st.session_state.estimated_wind = None
        
    # For gear comparison page
    if 'gear1_data' not in st.session_state:
        st.session_state.gear1_data = None
        
    if 'gear2_data' not in st.session_state:
        st.session_state.gear2_data = None
    
    # Add navigation tabs at the top of the main content
    tabs = ["📊 Track Analysis", "🔄 Gear Comparison"]
    selected_tab = st.radio("Navigation", tabs, horizontal=True, label_visibility="collapsed")
    
    # Load the gear comparison module once
    from pages.gear_comparison import st_main as gear_comparison
    
    # Update session state based on selected tab
    if selected_tab == "📊 Track Analysis":
        st.session_state.page = "Track Analysis"
    else:
        st.session_state.page = "Gear Comparison"
    
    # Display content based on the selected tab
    if st.session_state.page == "Track Analysis":
        single_track_analysis()
    else:
        gear_comparison()
    
    logger.info(f"App started - {st.session_state.page} page")


def single_track_analysis():
    """Single track analysis page with session state persistence"""
    st.header("Track Analysis")
    st.markdown("Analyze your wingfoil tracks to improve performance")
    
    # Sidebar parameters
    with st.sidebar:
        # Clean up sidebar by removing redundant headers
        st.header("Track Analysis Parameters")
        
        # Wind direction section
        st.subheader("Wind Direction")
        if 'wind_mode' not in st.session_state:
            st.session_state.wind_mode = "Auto-detect"  # Default to auto-detect
            
        wind_mode = st.radio(
            "Wind Direction Mode",
            ["Auto-detect", "Manual"], 
            index=0 if st.session_state.wind_mode == "Auto-detect" else 1,
            horizontal=True,
            key="wind_mode_radio"
        )
        
        # Update wind mode in session state
        st.session_state.wind_mode = wind_mode
        
        # Wind direction input or display
        if wind_mode == "Manual":
            wind_direction = st.number_input(
                "Wind Direction (°)", 
                min_value=0, 
                max_value=359, 
                value=int(st.session_state.wind_direction) if st.session_state.wind_direction is not None else 90,
                help="Direction the wind is coming FROM (0-359°)"
            )
            # Save to session state
            st.session_state.wind_direction = wind_direction
            auto_detect_wind = False
        else:
            st.info("Wind direction will be automatically estimated from your track data")
            auto_detect_wind = True
            
            # If we already have an estimated wind direction, show the fine-tuning slider
            if st.session_state.estimated_wind is not None:
                estimated = st.session_state.estimated_wind
                st.write(f"Estimated: {estimated:.1f}°")
                adjusted_wind = st.slider(
                    "Fine-tune Wind Direction", 
                    min_value=max(0, int(estimated) - 20),
                    max_value=min(359, int(estimated) + 20),
                    value=int(st.session_state.wind_direction) if st.session_state.wind_direction is not None else int(estimated)
                )
                wind_direction = adjusted_wind
                st.session_state.wind_direction = wind_direction
            else:
                # No estimate yet
                wind_direction = st.session_state.wind_direction
        
        # Segment detection parameters
        st.subheader("Segment Detection")
        angle_tolerance = st.slider("Angle Tolerance (°)", 
                                   min_value=5, max_value=20, value=12,
                                   help="How much the bearing can vary within a segment")
        
        # Minimum criteria
        min_duration = st.slider("Min Duration (sec)", min_value=1, max_value=60, value=10)
        min_distance = st.slider("Min Distance (m)", min_value=10, max_value=200, value=50)
        min_speed = st.slider("Min Speed (knots)", min_value=5.0, max_value=30.0, value=10.0, step=0.5)
        
        st.subheader("Speed Filter")
        active_speed_threshold = st.slider("Active Speed Threshold (knots)", 
                                          min_value=0.0, max_value=10.0, value=5.0, step=0.5,
                                          help="Speeds below this will be excluded from average speed calculation")

        min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
        
        # Advanced options
        st.subheader("Advanced Options")
        advanced_mode = st.checkbox("Advanced Mode", value=False, 
                                   help="Enable advanced features like wind estimation method selection")
        
        if advanced_mode:
            st.info("""
            **Advanced Mode gives you access to:**
            - Wind estimation method selection
            - Additional analysis options
            - Fine-tuning of algorithm parameters
            """, icon="ℹ️")
        
        if advanced_mode:
            wind_estimation_method = st.radio(
                "Wind Estimation Method",
                ["Simple", "Complex"],
                index=0,
                help="Choose the algorithm for wind direction estimation"
            )
            
            st.caption("""
            **Simple Method:** Works best for real-world tracks. Analyzes what angles you sailed and finds the most 
            consistent wind direction to explain them. Preferred for most situations.
            
            **Complex Method:** Uses a more sophisticated algorithm that works well for synthetic or 
            "perfect" data but can be less reliable with real tracks.
            """)
            
            use_simple_method = wind_estimation_method == "Simple"
        else:
            use_simple_method = True  # Default to simple method
            
        # Add wind angle explanation at the bottom of the sidebar
        st.divider()
        st.subheader("Wind Angle Explanation")
        st.markdown("""
        The angles shown in the analysis are measured as **degrees off the wind direction**:
        - **0°** means sailing directly into the wind (impossible)
        - **45°** is a typical upwind angle
        - **90°** is sailing across the wind (beam reach)
        - **180°** is sailing directly downwind
        
        Smaller angles are better for upwind performance, larger angles are better for downwind.
        """)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a GPX file", type=['gpx'], key="track_analysis_uploader")
    
    # Button to clear data
    if st.session_state.track_data is not None:
        if st.button("Clear Current Data", key="clear_track_data"):
            st.session_state.track_data = None
            st.session_state.track_metrics = None
            st.session_state.track_stretches = None
            st.session_state.track_name = None
            st.session_state.wind_direction = 90
            st.session_state.estimated_wind = None
            st.experimental_rerun()
    
    # Process new file upload or use session state data
    if uploaded_file is not None:
        logger.info(f"Processing uploaded file: {uploaded_file.name}")
        with st.spinner("Processing GPX data..."):
            # Load GPX data
            try:
                gpx_result = load_gpx_file(uploaded_file)
                
                # Handle both old and new return formats
                if isinstance(gpx_result, tuple):
                    gpx_data, metadata = gpx_result
                    track_name = metadata.get('name', 'Unknown Track')
                else:
                    gpx_data = gpx_result
                    track_name = 'Unknown Track'
                    
                # Store in session state
                st.session_state.track_data = gpx_data
                st.session_state.track_name = track_name
                
                logger.info(f"Loaded GPX file with {len(gpx_data)} points")
            except Exception as e:
                logger.error(f"Error loading GPX file: {e}")
                st.error(f"Error loading GPX file: {e}")
                gpx_data = pd.DataFrame()
                st.session_state.track_data = None
                st.session_state.track_name = None
    elif st.session_state.track_data is not None:
        # Use data from session state
        gpx_data = st.session_state.track_data
        track_name = st.session_state.track_name
        st.info(f"Using previously loaded data: {track_name}")
    else:
        gpx_data = pd.DataFrame()
    
    # Calculate basic track metrics with active speed filter
    if not gpx_data.empty:
        metrics = calculate_track_metrics(gpx_data, min_speed_knots=active_speed_threshold)
        # Store metrics in session state
        st.session_state.track_metrics = metrics
        
        # Display track summary
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Track Summary: {track_name}")
            st.write(f"📅 Date: {metrics['date']}")
            st.write(f"⏱️ Total Duration: {metrics['duration']}")
            
            # Show active metrics if available
            if 'active_duration' in metrics:
                active_percent = (metrics['active_duration'].total_seconds() / metrics['total_duration_seconds']) * 100 if metrics['total_duration_seconds'] > 0 else 0
                st.write(f"⏱️ Active Duration: {metrics['active_duration']} ({active_percent:.1f}%)")
        
        with col2:
            st.metric("📏 Total Distance", f"{metrics['distance']:.2f} km")
            
            # Show weighted average speed (active only)
            if 'weighted_avg_speed' in metrics:
                st.metric("⚡ Active Average Speed", f"{metrics['weighted_avg_speed']:.2f} knots", 
                         help=f"Average speed when moving above {active_speed_threshold} knots")
            else:
                st.metric("⚡ Average Speed", f"{metrics['avg_speed']:.2f} knots")
            
            # Show comparison if different
            if 'overall_avg_speed' in metrics and abs(metrics['overall_avg_speed'] - metrics['weighted_avg_speed']) > 0.1:
                st.caption(f"Overall average (including stops): {metrics['overall_avg_speed']:.2f} knots")
        
        # Find consistent angle stretches
        stretches = find_consistent_angle_stretches(
            gpx_data, angle_tolerance, min_duration, min_distance
        )
        
        if not stretches.empty:
            # Filter by minimum speed
            stretches = stretches[stretches['speed'] >= min_speed_ms]
            
            if not stretches.empty:
                # Save to session state
                st.session_state.track_stretches = stretches
                
                # Always try to estimate wind direction for comparison
                estimated_wind = None
                try:
                    estimated_wind = estimate_wind_direction(stretches, use_simple_method=use_simple_method)
                    if estimated_wind is not None:
                        logger.info(f"Estimated wind direction: {estimated_wind:.1f}° (using {'simple' if use_simple_method else 'complex'} method)")
                        
                        # Save to session state
                        st.session_state.estimated_wind = estimated_wind
                        
                        # If auto-detect is on, use the estimated wind
                        if auto_detect_wind:
                            # Display success and use the estimated value
                            wind_direction = estimated_wind
                            st.session_state.wind_direction = wind_direction
                            st.sidebar.success(f"Using estimated wind direction: {estimated_wind:.1f}°")
                        else:
                            # In manual mode, just show the estimated value for comparison
                            st.sidebar.info(f"Estimated wind direction: {estimated_wind:.1f}°")
                    else:
                        if auto_detect_wind:
                            logger.warning("Could not estimate wind direction, using default")
                            st.sidebar.warning("Could not estimate wind direction")
                except Exception as e:
                    logger.error(f"Error estimating wind direction: {e}")
                    if auto_detect_wind:
                        st.sidebar.error(f"Error estimating wind direction")
                
                # If we're using auto but couldn't estimate, fall back to default
                if auto_detect_wind and estimated_wind is None:
                    # We keep the default or manually overridden value of wind_direction
                    pass
                
                # Calculate angles relative to wind
                stretches = analyze_wind_angles(stretches, wind_direction)
                
                # Save the analyzed stretches to session state
                st.session_state.track_stretches = stretches
                
                # Display visualization and analysis
                col1, col2 = st.columns(2)
                
                # When displaying the map, pass the estimated wind:
                with col1:
                    # Display interactive map for segment selection
                    st.subheader("Track Map (Click segments to select/deselect)")
                    
                    # Display the map - this now uses st.component.html which doesn't return segment IDs
                    # directly but updates session_state via JavaScript
                    display_track_map(gpx_data, stretches, wind_direction, estimated_wind)
                    
                    # MOVE SEGMENT SELECTION HERE - RIGHT UNDER THE MAP
                    # Create a header for segment filters
                    st.subheader("Segment Selection")
                    
                    # Set default filter state
                    if 'filter_changes' not in st.session_state:
                        st.session_state.filter_changes = {
                            'upwind_selected': False,
                            'downwind_selected': False,
                            'suspicious_removed': False,
                            'best_speed_selected': False
                        }
                    
                    # First, make sure filter_changes is initialized
                    if 'filter_changes' not in st.session_state:
                        st.session_state.filter_changes = {
                            'upwind_selected': False,
                            'downwind_selected': False,
                            'suspicious_removed': False,
                            'best_speed_selected': False
                        }
                    
                    # Create a clearer filter section
                    st.write("**Select Segments:**")
                    
                    # Create two rows of buttons for better organization
                    row1_cols = st.columns(4)
                    
                    # 1st row - Selection and type filters
                    with row1_cols[0]:
                        if st.button("🔄 All", key="all_btn", help="Select all segments"):
                            # Reset all filters
                            st.session_state.filter_changes = {
                                'upwind_selected': False,
                                'downwind_selected': False,
                                'suspicious_removed': False,
                                'best_speed_selected': False
                            }
                            # Select all segments
                            st.session_state.selected_segments = display_df['original_index'].tolist()
                            st.experimental_rerun()
                    
                    with row1_cols[1]:
                        if st.button("❌ None", key="none_btn", help="Deselect all segments"):
                            # Reset all filters
                            st.session_state.filter_changes = {
                                'upwind_selected': False,
                                'downwind_selected': False,
                                'suspicious_removed': False,
                                'best_speed_selected': False
                            }
                            # Deselect all segments
                            st.session_state.selected_segments = []
                            st.experimental_rerun()
                    
                    # Use checkboxes instead of buttons for filters
                    with row1_cols[2]:
                        upwind = st.checkbox(
                            "⬆️ Upwind", 
                            value=st.session_state.filter_changes['upwind_selected'],
                            key="upwind_check",
                            help="Include upwind segments"
                        )
                        # Update filter state
                        st.session_state.filter_changes['upwind_selected'] = upwind
                    
                    with row1_cols[3]:
                        downwind = st.checkbox(
                            "⬇️ Downwind", 
                            value=st.session_state.filter_changes['downwind_selected'],
                            key="downwind_check",
                            help="Include downwind segments"
                        )
                        # Update filter state
                        st.session_state.filter_changes['downwind_selected'] = downwind
                    
                    # 2nd row - Quality filters
                    row2_cols = st.columns(4)
                    
                    with row2_cols[0]:
                        no_suspicious = st.checkbox(
                            "⚠️ No Suspicious", 
                            value=st.session_state.filter_changes['suspicious_removed'],
                            key="suspicious_check",
                            help="Exclude segments with suspicious angles"
                        )
                        # Update filter state
                        st.session_state.filter_changes['suspicious_removed'] = no_suspicious
                    
                    with row2_cols[1]:
                        fastest = st.checkbox(
                            "⚡ Fastest Only", 
                            value=st.session_state.filter_changes['best_speed_selected'],
                            key="speed_check",
                            help="Include only the fastest segments"
                        )
                        # Update filter state
                        st.session_state.filter_changes['best_speed_selected'] = fastest
                    
                    # Add Apply button in the last column
                    with row2_cols[3]:
                        apply_button = st.button("✅ Apply Filters", type="primary", key="apply_filters")
                    
                    # Store the segment data in session state if not already there
                    if 'segment_data' not in st.session_state:
                        st.session_state.segment_data = stretches.copy()
                    
                    # Create a DataFrame with renamed columns for clarity
                    display_cols = ['sailing_type', 'bearing', 'angle_to_wind', 
                                  'distance', 'speed', 'duration', 'tack', 'upwind_downwind']
                    
                    display_df = stretches[display_cols].copy()
                    
                    # Store original index before resetting
                    display_df['original_index'] = display_df.index
                    
                    # Add index as segment ID 
                    display_df = display_df.reset_index()
                    
                    # Flag suspicious values (small angles to wind)
                    display_df['suspicious'] = display_df['angle_to_wind'] < 15
                    
                    # Add a column for segment selection
                    # Initialize selected_segments with all original indices if not already set
                    if ('selected_segments' not in st.session_state or 
                        not isinstance(st.session_state.selected_segments, list)):
                        # Default to all segments selected - use original indices
                        st.session_state.selected_segments = display_df['original_index'].tolist()
                    
                    # Rename columns to be clearer
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
                    
                    # Initialize filter indicators
                    filter_text = []
                    
                    # Filter changes are now handled directly by checkboxes
                    # The checkboxes automatically update st.session_state.filter_changes
                    
                    # Apply all filters together to get the correct selection
                    
                    # Start with all segments
                    all_segments = display_df['original_index'].tolist()
                    filtered_segments = all_segments.copy()
                    
                    # Apply direction filters if active
                    if st.session_state.filter_changes['upwind_selected'] and not st.session_state.filter_changes['downwind_selected']:
                        # Only include upwind segments
                        upwind_segments = display_df[display_df['upwind_downwind'] == 'Upwind']['original_index'].tolist()
                        filtered_segments = [s for s in filtered_segments if s in upwind_segments]
                        filter_text.append("Upwind only")
                    elif st.session_state.filter_changes['downwind_selected'] and not st.session_state.filter_changes['upwind_selected']:
                        # Only include downwind segments
                        downwind_segments = display_df[display_df['upwind_downwind'] == 'Downwind']['original_index'].tolist()
                        filtered_segments = [s for s in filtered_segments if s in downwind_segments]
                        filter_text.append("Downwind only")
                    elif st.session_state.filter_changes['upwind_selected'] and st.session_state.filter_changes['downwind_selected']:
                        # Both selected means all segments (no direction filtering)
                        filter_text.append("All directions")
                    
                    # Apply suspicious filter if active
                    if st.session_state.filter_changes['suspicious_removed']:
                        # Identify suspicious segments (angle_to_wind < 15°)
                        suspicious_segments = display_df[display_df['suspicious']]['original_index'].tolist()
                        
                        if suspicious_segments:
                            # Get the logger from global scope
                            logger.info(f"Removing {len(suspicious_segments)} suspicious segments: {suspicious_segments}")
                            
                            # Remove suspicious segments
                            filtered_segments = [s for s in filtered_segments if s not in suspicious_segments]
                            
                            # Double-check results
                            still_suspicious = [s for s in filtered_segments if s in suspicious_segments]
                            if still_suspicious:
                                logger.error(f"Failed to remove suspicious segments: {still_suspicious}")
                            
                        filter_text.append("No suspicious angles")
                    
                    # Apply speed filter if active
                    if st.session_state.filter_changes['best_speed_selected']:
                        # Get the top 25% segments by speed
                        speed_threshold = display_df['speed (knots)'].quantile(0.75)
                        fast_segments = display_df[display_df['speed (knots)'] >= speed_threshold]['original_index'].tolist()
                        filtered_segments = [s for s in filtered_segments if s in fast_segments]
                        filter_text.append(f"Fastest (>{speed_threshold:.1f} knots)")
                    
                    # Update the selected segments to contain the original indices
                    st.session_state.selected_segments = filtered_segments
                        
                    # Add filter indicator UI with better styling
                    if filter_text:
                        st.success(f"**Active filters:** {', '.join(filter_text)}")
                    else:
                        st.info("**No filters active** - showing all segments")
                    
                    # Apply immediately when button is clicked
                    if apply_button:
                        st.experimental_rerun()
                    
                    # Show selection stats - only if we have valid selected_segments in session state
                    if ('selected_segments' in st.session_state and 
                        isinstance(st.session_state.selected_segments, list) and 
                        len(st.session_state.selected_segments) > 0):
                        
                        selected_count = len(st.session_state.selected_segments)
                        total_count = len(stretches)
                        selection_percentage = (selected_count / total_count) * 100
                        st.caption(f"Selected {selected_count} of {total_count} segments ({selection_percentage:.1f}%)")
                    
                    # Add a warning for suspicious values
                    if display_df['suspicious'].any():
                        suspicious_count = display_df['suspicious'].sum()
                        suspicious_segments = display_df[display_df['suspicious']]['original_index'].tolist()
                        suspicious_angles = display_df[display_df['suspicious']]['angle off wind (°)'].tolist()
                        
                        angles_text = ", ".join([f"{angle:.1f}°" for angle in suspicious_angles])
                        
                        st.warning(
                            f"⚠️ {suspicious_count} segments have suspiciously small angles to wind (< 15°): {angles_text}. " +
                            f"These are shown with dashed lines on the map."
                        )
                    
                    # Calculate average angle from selected segments
                    from utils.calculations import calculate_average_angle_from_segments
                    
                    if ('selected_segments' in st.session_state and 
                        isinstance(st.session_state.selected_segments, list) and 
                        len(st.session_state.selected_segments) > 0):
                        
                        filtered_stretches = stretches.loc[stretches.index.isin(st.session_state.selected_segments)]
                        angle_results = calculate_average_angle_from_segments(filtered_stretches)
                        
                        # Display angle calculation results
                        if angle_results['average_angle'] is not None:
                            st.info(f"Average angle off the wind: **{angle_results['average_angle']:.1f}°**")
                            
                            # Show tack-specific info
                            if angle_results['port_count'] > 0 and angle_results['starboard_count'] > 0:
                                st.caption(f"Port avg: {angle_results['port_average']:.1f}° ({angle_results['port_count']} segments)")
                                st.caption(f"Starboard avg: {angle_results['starboard_average']:.1f}° ({angle_results['starboard_count']} segments)")
                            elif angle_results['port_count'] > 0:
                                st.caption(f"Using only Port tack data ({angle_results['port_count']} segments)")
                            elif angle_results['starboard_count'] > 0:
                                st.caption(f"Using only Starboard tack data ({angle_results['starboard_count']} segments)")
                
                with col2:
                    # Use the filtered segments for visualization
                    st.subheader("Polar Performance")
                    
                    # Get the filtered stretches for visualization
                    if ('selected_segments' in st.session_state and 
                        isinstance(st.session_state.selected_segments, list) and 
                        len(st.session_state.selected_segments) > 0):
                        
                        filtered_stretches = stretches.loc[stretches.index.isin(st.session_state.selected_segments)]
                        source_note = f"(using {len(filtered_stretches)} selected segments)"
                    else:
                        filtered_stretches = stretches
                        source_note = f"(using all {len(stretches)} segments)"
                    
                    if len(filtered_stretches) > 2:
                        fig = plot_polar_diagram(filtered_stretches, wind_direction)
                        st.pyplot(fig)
                        st.caption(source_note)
                    else:
                        st.info("Not enough data for polar plot (need at least 3 segments)")
                
                # Wind angle explanation moved to sidebar
                
                # Display upwind/downwind analysis based on selected segments
                st.subheader("Wind Angle Analysis")
                
                # Get the filtered stretches for analysis
                if ('selected_segments' in st.session_state and 
                    isinstance(st.session_state.selected_segments, list) and 
                    len(st.session_state.selected_segments) > 0):
                    
                    analysis_stretches = stretches.loc[stretches.index.isin(st.session_state.selected_segments)]
                    source_note = f"(based on {len(analysis_stretches)} selected segments)"
                else:
                    analysis_stretches = stretches
                    source_note = f"(based on all {len(stretches)} segments)"
                
                # Add note about which segments are being used
                st.caption(source_note)
                
                # Split into upwind/downwind
                upwind = analysis_stretches[analysis_stretches['angle_to_wind'] < 90]
                downwind = analysis_stretches[analysis_stretches['angle_to_wind'] >= 90]
                
                if not upwind.empty or not downwind.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Upwind Performance")
                        if not upwind.empty:
                            # Display upwind stats
                            port = upwind[upwind['tack'] == 'Port']
                            starboard = upwind[upwind['tack'] == 'Starboard']
                            
                            if not port.empty:
                                best_port = port.loc[port['angle_to_wind'].idxmin()]
                                # For upwind, smaller angle to wind is better
                                st.metric("Best Port Upwind Angle", 
                                        f"{best_port['angle_to_wind']:.1f}° off wind", 
                                        f"{best_port['speed']:.1f} knots")
                                st.caption(f"Bearing: {best_port['bearing']:.1f}°")
                            
                            if not starboard.empty:
                                best_stbd = starboard.loc[starboard['angle_to_wind'].idxmin()]
                                st.metric("Best Starboard Upwind Angle", 
                                        f"{best_stbd['angle_to_wind']:.1f}° off wind", 
                                        f"{best_stbd['speed']:.1f} knots")
                                st.caption(f"Bearing: {best_stbd['bearing']:.1f}°")
                        else:
                            st.info("No upwind data in selection")
                    
                    with col2:
                        st.markdown("#### Downwind Performance")
                        if not downwind.empty:
                            # Display downwind stats
                            port = downwind[downwind['tack'] == 'Port']
                            starboard = downwind[downwind['tack'] == 'Starboard']
                            
                            if not port.empty:
                                best_port = port.loc[port['angle_to_wind'].idxmax()]
                                # For downwind, larger angle to wind is better
                                st.metric("Best Port Downwind Angle", 
                                        f"{best_port['angle_to_wind']:.1f}° off wind", 
                                        f"{best_port['speed']:.1f} knots")
                                st.caption(f"Bearing: {best_port['bearing']:.1f}°")
                            
                            if not starboard.empty:
                                best_stbd = starboard.loc[starboard['angle_to_wind'].idxmax()]
                                st.metric("Best Starboard Downwind Angle", 
                                        f"{best_stbd['angle_to_wind']:.1f}° off wind", 
                                        f"{best_stbd['speed']:.1f} knots")
                                st.caption(f"Bearing: {best_stbd['bearing']:.1f}°")
                        else:
                            st.info("No downwind data in selection")
                else:
                    st.warning("No valid segments in current selection. Please select at least one segment.")
                
                # Plot bearing distribution based on selected segments
                st.subheader("Bearing Distribution")
                
                # Use the same filtered stretches for the plot
                if ('selected_segments' in st.session_state and 
                    isinstance(st.session_state.selected_segments, list) and 
                    len(st.session_state.selected_segments) > 0):
                    
                    filtered_stretches = stretches.loc[stretches.index.isin(st.session_state.selected_segments)]
                    source_note = f"(based on {len(filtered_stretches)} selected segments)"
                else:
                    filtered_stretches = stretches
                    source_note = f"(based on all {len(stretches)} segments)"
                
                # Add note about which segments are being used
                if len(filtered_stretches) > 0:
                    fig = plot_bearing_distribution(filtered_stretches, wind_direction)
                    st.pyplot(fig)
                    st.caption(source_note)
                else:
                    st.warning("No segments selected for bearing distribution plot.")
                
                # Display more prominent segment selection UI
                st.subheader("Segment Selection")
                
                # Set default filter state
                if 'filter_changes' not in st.session_state:
                    st.session_state.filter_changes = {
                        'upwind_selected': False,
                        'downwind_selected': False,
                        'suspicious_removed': False,
                        'best_speed_selected': False
                    }
                
                # Filter buttons are now in the main UI above, so no need for duplicate buttons here
                
                # Store the segment data in session state if not already there
                if 'segment_data' not in st.session_state:
                    st.session_state.segment_data = stretches.copy()
                
                # Create a DataFrame with renamed columns for clarity
                display_cols = ['sailing_type', 'bearing', 'angle_to_wind', 
                              'distance', 'speed', 'duration', 'tack', 'upwind_downwind']
                
                display_df = stretches[display_cols].copy()
                
                # Store original index before resetting
                display_df['original_index'] = display_df.index
                
                # Add index as segment ID 
                display_df = display_df.reset_index()
                
                # Flag suspicious values (small angles to wind)
                display_df['suspicious'] = display_df['angle_to_wind'] < 15
                
                # Add a column for segment selection
                # Initialize selected_segments with all original indices if not already set
                if ('selected_segments' not in st.session_state or 
                    not isinstance(st.session_state.selected_segments, list)):
                    # Default to all segments selected - use original indices
                    st.session_state.selected_segments = display_df['original_index'].tolist()
                
                # Rename columns to be clearer
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
                
                # Initialize filter indicators
                filter_text = []
                
                # Apply all filters together to get the correct selection
                
                # Start with all segments
                all_segments = display_df['segment_id'].tolist()
                filtered_segments = all_segments.copy()
                
                # Apply direction filters if active
                if st.session_state.filter_changes['upwind_selected'] and not st.session_state.filter_changes['downwind_selected']:
                    # Only include upwind segments
                    upwind_segments = display_df[display_df['upwind_downwind'] == 'Upwind']['segment_id'].tolist()
                    filtered_segments = [s for s in filtered_segments if s in upwind_segments]
                    filter_text.append("Upwind only")
                elif st.session_state.filter_changes['downwind_selected'] and not st.session_state.filter_changes['upwind_selected']:
                    # Only include downwind segments
                    downwind_segments = display_df[display_df['upwind_downwind'] == 'Downwind']['segment_id'].tolist()
                    filtered_segments = [s for s in filtered_segments if s in downwind_segments]
                    filter_text.append("Downwind only")
                elif st.session_state.filter_changes['upwind_selected'] and st.session_state.filter_changes['downwind_selected']:
                    # Both selected means all segments (no direction filtering)
                    filter_text.append("All directions")
                
                # Apply suspicious filter if active
                if st.session_state.filter_changes['suspicious_removed']:
                    # Identify suspicious segments (angle_to_wind < 15°)
                    suspicious_segments = display_df[display_df['suspicious']]['segment_id'].tolist()
                    
                    if suspicious_segments:
                        # Get the logger from global scope
                        logger.info(f"Removing {len(suspicious_segments)} suspicious segments: {suspicious_segments}")
                        
                        # Remove suspicious segments
                        filtered_segments = [s for s in filtered_segments if s not in suspicious_segments]
                        
                        # Double-check results
                        still_suspicious = [s for s in filtered_segments if s in suspicious_segments]
                        if still_suspicious:
                            logger.error(f"Failed to remove suspicious segments: {still_suspicious}")
                        
                    filter_text.append("No suspicious angles")
                
                # Apply speed filter if active
                if st.session_state.filter_changes['best_speed_selected']:
                    # Get the top 25% segments by speed
                    speed_threshold = display_df['speed (knots)'].quantile(0.75)
                    fast_segments = display_df[display_df['speed (knots)'] >= speed_threshold]['segment_id'].tolist()
                    filtered_segments = [s for s in filtered_segments if s in fast_segments]
                    filter_text.append(f"Fastest (>{speed_threshold:.1f} knots)")
                
                # Map segment IDs back to original indices for proper filtering of stretches DataFrame
                selected_original_indices = display_df[display_df['segment_id'].isin(filtered_segments)]['original_index'].tolist()
                
                # Update the selected segments to contain the original indices
                st.session_state.selected_segments = selected_original_indices
                    
                # Add filter indicator UI with better styling
                if filter_text:
                    st.success(f"**Active filters:** {', '.join(filter_text)}")
                else:
                    st.info("**No filters active** - showing all segments")
                
                # Add a warning for suspicious values
                if display_df['suspicious'].any():
                    st.warning(f"⚠️ {display_df['suspicious'].sum()} segments have suspiciously small angles to wind (< 15°). " +
                              f"These segments are shown with dashed lines on the map. Consider deselecting them or adjusting the wind direction.")
                
                # Display summary of current selection
                if (isinstance(st.session_state.selected_segments, list)):
                    selected_count = len(st.session_state.selected_segments)
                    total_count = len(display_df)
                else:
                    selected_count = 0
                    total_count = len(display_df)
                
                # Add a button to apply filter and refresh
                col_refresh = st.columns([3, 1])
                with col_refresh[1]:
                    if st.button("Apply & Refresh"):
                        # This will trigger a re-run with current selections
                        st.experimental_rerun()
                
                if selected_count > 0:
                    # Get stats on the selected segments
                    selected_df = display_df[display_df['segment_id'].isin(st.session_state.selected_segments)]
                    
                    # Count by type
                    upwind_count = sum(selected_df['upwind_downwind'] == 'Upwind')
                    downwind_count = sum(selected_df['upwind_downwind'] == 'Downwind')
                    port_count = sum(selected_df['tack'] == 'Port')
                    starboard_count = sum(selected_df['tack'] == 'Starboard')
                    
                    # Display selection summary
                    with col_refresh[0]:
                        st.info(f"Selected {selected_count} of {total_count} segments: " + 
                            f"{upwind_count} upwind, {downwind_count} downwind, " +
                            f"{port_count} port, {starboard_count} starboard")
                else:
                    with col_refresh[0]:
                        st.warning("No segments selected. Use the buttons above to select segments.")
                
                # Show detailed segment selection with checkboxes
                with st.expander("Detailed Segment Selection", expanded=False):
                    # Show the segments grouped by type with checkboxes
                    st.write("**Select individual segments:**")
                    
                    # Group by sailing type for better organization
                    segment_types = display_df['sailing_type'].unique()
                    
                    for sailing_type in segment_types:
                        st.write(f"**{sailing_type}:**")
                        
                        # Get segments of this type
                        type_segments = display_df[display_df['sailing_type'] == sailing_type]
                        
                        # Show in 3 columns
                        check_cols = st.columns(3)
                        
                        # Distribute segments across columns
                        segments_per_col = len(type_segments) // 3 + 1
                        
                        col_idx = 0
                        segment_count = 0
                        
                        for i, row in type_segments.iterrows():
                            segment_id = row['segment_id']
                            angle = row['angle off wind (°)']
                            speed = row['speed (knots)']
                            is_suspicious = row['suspicious']
                            
                            # Switch to next column if needed
                            if segment_count >= segments_per_col:
                                col_idx = (col_idx + 1) % 3
                                segment_count = 0
                            
                            # Format the label based on whether it's suspicious
                            if is_suspicious:
                                label = f"⚠️ #{segment_id}: {angle}°, {speed}kn"
                            else:
                                label = f"#{segment_id}: {angle}°, {speed}kn"
                            
                            # Create a checkbox for each segment in the appropriate column
                            with check_cols[col_idx]:
                                is_selected = st.checkbox(
                                    label, 
                                    value=segment_id in st.session_state.selected_segments,
                                    key=f"segment_{segment_id}"
                                )
                                
                                # Update selection
                                if is_selected and segment_id not in st.session_state.selected_segments:
                                    st.session_state.selected_segments.append(segment_id)
                                elif not is_selected and segment_id in st.session_state.selected_segments:
                                    st.session_state.selected_segments.remove(segment_id)
                            
                            segment_count += 1
                
                # Display segment data table
                st.subheader(f"Segment Data")
                
                # Use only the selected segments for display
                filtered_display_df = display_df[display_df['segment_id'].isin(st.session_state.selected_segments)]
                
                # Show the filtered dataframe
                display_cols = ['segment_id', 'sailing_type', 'heading (°)', 'angle off wind (°)', 
                               'speed (knots)', 'distance (m)', 'duration (sec)']
                
                if not filtered_display_df.empty:
                    st.dataframe(filtered_display_df[display_cols], use_container_width=True)
                
                # Data download
                csv = stretches.to_csv(index=False)
                st.download_button(
                    "Download Analysis as CSV",
                    data=csv,
                    file_name="wingfoil_analysis.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No segments meet minimum speed criteria.")
        else:
            st.warning("No consistent angle segments found. Try adjusting parameters.")
    else:
        if uploaded_file is not None:
            st.error("Unable to parse GPX data. Check file format.")

if __name__ == "__main__":
    main()