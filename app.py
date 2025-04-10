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
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles as analyze_wind_angles_orig, estimate_wind_direction

# Rename to avoid conflicts
analyze_wind_angles = analyze_wind_angles_orig
from utils.visualization import display_track_map, plot_polar_diagram

def main():
    st.set_page_config(
        layout="wide", 
        page_title="WingWizard - Strava Analyzer",
        page_icon="🪂",
        initial_sidebar_state="expanded",
        menu_items={
            'About': "WingWizard - Analyze your wingfoil tracks to improve performance and have fun doing it!"
        }
    )
    
    # Custom CSS for modern styling with dark mode compatibility
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px 4px 0px 0px;
        padding: 5px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 104, 201, 0.1);
        border-bottom: 2px solid var(--primary-color, rgb(0, 104, 201));
    }
    div.block-container {
        padding-top: 1rem;
    }
    h1 {
        font-size: 2.5rem;
        color: var(--primary-color, #0068C9);
        margin-bottom: 0.5rem;
    }
    h2 {
        margin-top: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .metric-value {
        color: var(--primary-color, #0068C9);
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.8rem;
        color: var(--text-color, #555);
    }
    /* Dark mode compatibility */
    @media (prefers-color-scheme: dark) {
        .highlight-container {
            background-color: rgba(0, 104, 201, 0.2) !important;
        }
        .card-metric {
            color: var(--primary-color, #4DA8FF) !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main title with emoji and creative name
    st.title("🪂 WingWizard")
    
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
    
    # Load the gear comparison module once (from modules to avoid sidebar page navigation)
    from modules.gear_comparison import st_main as gear_comparison
    
    # Create tabs-based navigation at the top of the page (simpler approach)
    selected_tab = st.radio(
        "Navigation",
        ["📚 Guide", "📊 Track Analysis", "🔄 Gear Comparison"],
        horizontal=True,
        label_visibility="collapsed",
        index=1 if st.session_state.page == "Track Analysis" else (0 if st.session_state.page == "Guide" else 2)
    )
    
    # Update session state based on selected tab
    if selected_tab == "📊 Track Analysis":
        st.session_state.page = "Track Analysis"
    elif selected_tab == "🔄 Gear Comparison":
        st.session_state.page = "Gear Comparison"
    else:
        st.session_state.page = "Guide"
    
    # Display content based on the selected page
    if st.session_state.page == "Track Analysis":
        single_track_analysis()
    elif st.session_state.page == "Gear Comparison":
        gear_comparison()
    else:
        # Guide page
        display_guide()
    
    logger.info(f"App started - {st.session_state.page} page")


def display_guide():
    """Display the guide page with instructions and help."""
    st.header("📚 WingWizard Guide")
    
    st.markdown("""
    Welcome to WingWizard, your tool for analyzing wingfoil sessions and improving your performance!
    
    This guide will help you understand how to use the app's features effectively.
    """)
    
    # Create expandable sections for different aspects of the app
    with st.expander("🌊 Getting Started", expanded=True):
        st.markdown("""
        ### How to Use WingWizard
        
        1. **Upload a GPX file** from your Strava or other GPS tracking app
        2. **Analyze your tracks** to see your performance at different wind angles
        3. **Save sessions** to compare different gear setups
        4. **Get insights** about your upwind and downwind performance
        
        The app uses wind direction to calculate your angles to the wind, which is crucial for understanding your wingfoiling performance.
        """)
        
        # Add screenshot or illustration
        st.info("📋 Use the sidebar navigation to switch between Track Analysis and Gear Comparison pages.")
    
    with st.expander("🔍 Track Analysis"):
        st.markdown("""
        ### Analyzing Your Tracks
        
        The Track Analysis page helps you understand your session performance:
        
        - **Wind Direction**: Either auto-detected or manually set
        - **Segment Detection**: Identifies consistent stretches of sailing
        - **Segment Filtering**: Select specific parts of your session to analyze
        - **Performance Analysis**: See your best upwind and downwind angles
        - **Polar Plot**: Visualize your speed at different angles to the wind
        
        #### Key Concepts
        
        - **Angle to Wind**: 0° is directly upwind (impossible), 90° is across the wind, 180° is directly downwind
        - **Tack**: Port (left hand forward) or Starboard (right hand forward)
        - **Suspicious Angles**: Angles too close to the wind (typically <20°) that are physically impossible and excluded from analysis
        """)
        
        # Add explanation with help icons
        st.info("ℹ️ The segment selection tools let you focus on specific parts of your session. Filter by upwind/downwind, remove suspicious data, or select only your fastest runs.")
    
    with st.expander("🔄 Gear Comparison"):
        st.markdown("""
        ### Comparing Different Gear
        
        The Gear Comparison page allows you to save and compare different sessions:
        
        - **Save sessions** from Track Analysis with your gear setup details
        - **Compare multiple sessions** to see how different gear performs
        - **Analyze performance differences** in upwind and downwind sailing
        - **Filter to upwind only** to focus on pointing performance
        
        #### Key Metrics
        
        - **Pointing Power**: Average of best port/starboard pointing angles (lower is better)
        - **Clustered Upwind Speed**: Speed at your best upwind angles
        - **Downwind Performance**: Maximum angle and speed downwind
        """)
        
        # Add explanation with help icons
        st.info("💡 For the most accurate gear comparisons, try to sail in similar wind conditions and use consistent wind direction estimation.")
    
    with st.expander("🧠 Advanced Tips"):
        st.markdown("""
        ### Getting the Most from WingWizard
        
        - **Wind Direction** is crucial - the auto-detection works well for most sessions, but you can manually adjust it
        - **Segment Detection** parameters can be tuned - adjust angle tolerance based on how consistent your tracks are
        - **Suspicious Angle Threshold** filters out implausible angles - 20° is usually good but adjust based on your gear
        - **Export to Comparison** preserves your selected segments and filters
        - **Auto-naming** generates session names based on your gear info
        """)
        
        # Add technical tip
        st.info("🔧 For advanced users: Wind estimation has two methods - 'Simple' works better for real-world tracks, while 'Complex' is optimized for perfect data.")


def single_track_analysis():
    """Single track analysis page with session state persistence"""
    
    # Initialize comparison data storage if not already present
    if 'gear_comparison_data' not in st.session_state:
        st.session_state.gear_comparison_data = []
        
    # Initialize export form visibility toggle
    if 'show_export_form' not in st.session_state:
        st.session_state.show_export_form = False
    
    # Show export form dialog if triggered
    if st.session_state.show_export_form and st.session_state.track_data is not None:
        with st.form("export_gear_data_form"):
            st.subheader("Export Session to Gear Comparison")
            
            # Get a copy of the current filtered stretches
            if ('selected_segments' in st.session_state and 
                isinstance(st.session_state.selected_segments, list) and 
                len(st.session_state.selected_segments) > 0 and
                'track_stretches' in st.session_state):
                
                current_stretches = st.session_state.track_stretches.loc[
                    st.session_state.track_stretches.index.isin(st.session_state.selected_segments)
                ].copy()
            else:
                if 'track_stretches' in st.session_state:
                    current_stretches = st.session_state.track_stretches.copy()
                else:
                    current_stretches = pd.DataFrame()
            
            # Main, most important gear info - focus on the essentials
            st.markdown("### Essential Gear Info")
            col1, col2 = st.columns(2)
            with col1:
                wing = st.text_input("Wing", placeholder="E.g., Duotone Unit 5m")
                foil = st.text_input("Foil", placeholder="E.g., Armstrong CF2400")
            
            with col2:
                wind_speed = st.number_input("Avg Wind Speed (knots)", min_value=0, max_value=50, value=0, step=1)
                auto_name = st.checkbox("Auto-generate session name", value=True)
            
            # Less important details in an expander
            with st.expander("More Details (Optional)"):
                # Board info
                board = st.text_input("Board", placeholder="E.g., Axis S-Series 5'2\"")
                
                # Wind info
                col1, col2 = st.columns(2)
                with col1:
                    wind_range = st.text_input("Wind Range", placeholder="E.g., 15-20 knots")
                    conditions = st.text_input("Conditions", placeholder="E.g., Choppy water, gusty")
                
                with col2:
                    location = st.text_input("Location", placeholder="E.g., San Francisco Bay")
                    session_date = st.date_input("Session Date", value=None)
                
                # Notes
                notes = st.text_area("Notes", placeholder="Any additional info about this session")
                
                # Manual session name override
                if not auto_name:
                    session_name = st.text_input(
                        "Custom Session Name", 
                        value=st.session_state.track_name if st.session_state.track_name else "Unnamed Session"
                    )
            
            # Form submission
            col1, col2 = st.columns([1, 1])
            with col1:
                cancel = st.form_submit_button("Cancel", type="secondary")
            with col2:
                submit = st.form_submit_button("Save to Comparison", type="primary")
            
            if submit:
                # Import the name generation function from the gear comparison module
                from pages.gear_comparison import generate_session_name
                
                # Generate automatic session name if checked
                if auto_name:
                    existing_names = [s['name'] for s in st.session_state.gear_comparison_data]
                    session_name = generate_session_name(
                        wing=wing,
                        foil=foil,
                        wind_speed=wind_speed,
                        original_name=st.session_state.track_name,
                        existing_names=existing_names
                    )
                
                # Create export data package
                export_data = {
                    'id': len(st.session_state.gear_comparison_data) + 1,
                    'name': session_name,
                    'date': session_date.isoformat() if session_date else None,
                    'wind_direction': st.session_state.wind_direction,
                    'wind_speed': wind_speed,
                    'wind_range': wind_range,
                    'board': board,
                    'foil': foil,
                    'wing': wing,
                    'location': location,
                    'conditions': conditions,
                    'notes': notes,
                    'metrics': st.session_state.track_metrics.copy() if st.session_state.track_metrics is not None else None,
                    'stretches': current_stretches
                }
                
                # Add to comparison data
                st.session_state.gear_comparison_data.append(export_data)
                
                # Close form
                st.session_state.show_export_form = False
                st.success(f"✅ '{session_name}' added to gear comparison!")
                st.rerun()
                
            if cancel:
                # Close form without saving
                st.session_state.show_export_form = False
                st.rerun()
    
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
                    value=int(st.session_state.wind_direction) if st.session_state.wind_direction is not None else int(estimated),
                    key="wind_fine_tune"
                )
                wind_direction = adjusted_wind
                
                # Update wind direction and force a refresh if it changed
                if wind_direction != st.session_state.wind_direction:
                    st.session_state.wind_direction = wind_direction
                    # Add a button to apply wind direction changes immediately
                    if st.button("Apply Wind Direction", type="primary"):
                        # This will trigger a rerun with the updated wind direction
                        st.rerun()
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
        
        # Always show suspicious angle threshold - this is important for accurate analysis
        # Default to 20 degrees - below this is usually not physically possible
        if 'suspicious_angle_threshold' not in st.session_state:
            st.session_state.suspicious_angle_threshold = 20
            
        suspicious_angle_threshold = st.slider(
            "Suspicious Angle Threshold (°)", 
            min_value=10, 
            max_value=35, 
            value=st.session_state.suspicious_angle_threshold,
            help="Angles closer to wind than this are considered suspicious and excluded from wind direction estimation"
        )
        
        # Update the threshold in session state
        st.session_state.suspicious_angle_threshold = suspicious_angle_threshold
        
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
            st.rerun()
    
    # Process new file upload or use session state data
    if uploaded_file is not None:
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
                
                progress_bar.progress(70)
                progress_text.markdown("💨 **Stage 4/5:** Analyzing wind patterns...")
                
                progress_bar.progress(90)
                progress_text.markdown("📊 **Stage 5/5:** Preparing visualization...")
                
                progress_bar.progress(100)
                progress_text.markdown("✅ **Analysis complete!** Your track is ready to explore.")
                
                # Add a bit of drama with a sleep
                import time
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error loading GPX file: {e}")
                st.error(f"Error loading GPX file: {e}")
                gpx_data = pd.DataFrame()
                st.session_state.track_data = None
                st.session_state.track_name = None
            
            # Clear the progress elements when done
            progress_container.empty()
    elif st.session_state.track_data is not None:
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
                    <span style="font-size: 0.9rem;">Ready to analyze! Adjust parameters in the sidebar if needed.</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        gpx_data = pd.DataFrame()
    
    # Calculate basic track metrics with active speed filter
    if not gpx_data.empty:
        metrics = calculate_track_metrics(gpx_data, min_speed_knots=active_speed_threshold)
        # Store metrics in session state
        st.session_state.track_metrics = metrics
        
        # Display track summary in a nice card-like container
        st.markdown("### 📌 Track Overview")
        
        with st.container(border=True):
            # Create a modern track summary layout
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            with col1:
                st.markdown(f"**🏄 {track_name}**")
                st.markdown(f"📅 **Date:** {metrics['date']}")
                
            with col2:
                # Duration metrics
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
                st.markdown("📏 **Distance**")
                st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{metrics['distance']:.2f} km</span>", 
                          unsafe_allow_html=True)
                
            with col4:
                # Speed metrics
                if 'weighted_avg_speed' in metrics:
                    st.markdown("⚡ **Average Speed**")
                    st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{metrics['weighted_avg_speed']:.1f} kn</span><br/>" + 
                              f"<span style='font-size:0.85rem; color:var(--text-color, #666);'>Above {active_speed_threshold} knots</span>", 
                              unsafe_allow_html=True)
                    
                    # Show comparison if different
                    if 'overall_avg_speed' in metrics and abs(metrics['overall_avg_speed'] - metrics['weighted_avg_speed']) > 0.1:
                        st.caption(f"Overall avg: {metrics['overall_avg_speed']:.1f} knots (with stops)")
                else:
                    st.markdown("⚡ **Average Speed**")
                    st.markdown(f"<span class='card-metric' style='font-size:1.5rem; font-weight:bold; color:var(--primary-color, #0068C9);'>{metrics['avg_speed']:.1f} kn</span>", 
                              unsafe_allow_html=True)
            
            # Export to comparison section
            export_col1, export_col2 = st.columns([3, 1])
            with export_col1:
                st.markdown("**💾 Want to save this session for gear comparison?**")
            with export_col2:
                if st.button("🔄 Export to Comparison", key="export_to_comparison", type="primary", use_container_width=True):
                    # Open a form to enter gear details
                    st.session_state.show_export_form = True
                    st.rerun()
        
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
                    # First try the new upwind tack analysis method
                    # This requires angles to be calculated with some initial wind direction
                    # We use default wind direction (90°) as starting point
                    initial_wind = 90
                    temp_stretches = analyze_wind_angles(stretches, initial_wind)
                    
                    # Try to get wind direction using the new tack-based method
                    from utils.analysis import estimate_wind_direction_from_upwind_tacks
                    # Pass the suspicious angle threshold from user settings
                    estimated_wind = estimate_wind_direction_from_upwind_tacks(
                        temp_stretches, 
                        suspicious_angle_threshold=suspicious_angle_threshold
                    )
                    
                    # If the new method succeeded, use it
                    if estimated_wind is not None:
                        logger.info(f"Estimated wind direction: {estimated_wind:.1f}° (using upwind tack analysis)")
                        estimation_method = "upwind tack analysis"
                    else:
                        # Fall back to standard method
                        estimated_wind = estimate_wind_direction(stretches, use_simple_method=use_simple_method)
                        if estimated_wind is not None:
                            logger.info(f"Estimated wind direction: {estimated_wind:.1f}° (using {'simple' if use_simple_method else 'complex'} method)")
                            estimation_method = "standard clustering"
                    
                    if estimated_wind is not None:
                        # Save to session state
                        st.session_state.estimated_wind = estimated_wind
                        
                        # If auto-detect is on, use the estimated wind
                        if auto_detect_wind:
                            # Display success and use the estimated value
                            wind_direction = estimated_wind
                            st.session_state.wind_direction = wind_direction
                            st.sidebar.success(f"Using estimated wind direction: {estimated_wind:.1f}° ({estimation_method})")
                        else:
                            # In manual mode, just show the estimated value for comparison
                            st.sidebar.info(f"Estimated wind direction: {estimated_wind:.1f}° ({estimation_method})")
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
                
                # Calculate angles relative to wind - this is critical for all visualizations
                # This ensures the angles and upwind/downwind classification use the current wind_direction
                stretches = analyze_wind_angles(stretches, wind_direction)
                
                # Save the analyzed stretches to session state - create a copy to avoid reference issues
                st.session_state.track_stretches = stretches.copy()
                
                # Reorganize the layout with tabs for better organization 
                st.write("## 🌊 Track Analysis Dashboard 🪂")
                
                # Create DataFrame for segment display
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
                
                # Flag suspicious values based on user's threshold setting
                display_df['suspicious'] = display_df['angle_to_wind'] < suspicious_angle_threshold
                
                # Add a column for segment selection
                # Initialize selected_segments with all original indices if not already set
                if ('selected_segments' not in st.session_state or 
                    not isinstance(st.session_state.selected_segments, list)):
                    # Default to all segments selected - use original indices
                    st.session_state.selected_segments = display_df['original_index'].tolist()
                    
                    # Set default filter state with suspicious segments excluded
                    st.session_state.filter_changes = {
                        'upwind_selected': False,
                        'downwind_selected': False,
                        'suspicious_removed': True,  # Default to true
                        'best_speed_selected': False
                    }
                    
                    # Default to excluding suspicious segments
                    suspicious_segments = display_df[display_df['suspicious']]['original_index'].tolist()
                    if suspicious_segments:
                        st.session_state.selected_segments = [s for s in st.session_state.selected_segments if s not in suspicious_segments]
                
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
                
                # SEGMENT SELECTION BAR - Placed before the map
                st.markdown("### 🔍 Segment Selection")
                
                # Set default filter state if not already set
                if 'filter_changes' not in st.session_state:
                    st.session_state.filter_changes = {
                        'upwind_selected': False,
                        'downwind_selected': False,
                        'suspicious_removed': True,  # Default to true
                        'best_speed_selected': False
                    }
                
                # Create a horizontal segment selection bar with filter status and wind re-estimation
                filter_container = st.container(border=True)
                
                top_row = filter_container.columns([1, 1, 2, 2, 1])
                # Left buttons
                with top_row[0]:
                    if st.button("🔄 All", key="all_btn", help="Select all segments", use_container_width=True):
                        st.session_state.filter_changes = {'upwind_selected': False, 'downwind_selected': False, 
                                                      'suspicious_removed': False, 'best_speed_selected': False}
                        st.session_state.selected_segments = display_df['original_index'].tolist()
                        st.rerun()
                with top_row[1]:
                    if st.button("❌ None", key="none_btn", help="Deselect all segments", use_container_width=True):
                        st.session_state.filter_changes = {'upwind_selected': False, 'downwind_selected': False, 
                                                      'suspicious_removed': False, 'best_speed_selected': False}
                        st.session_state.selected_segments = []
                        st.rerun()
                
                # Direction filter controls
                with top_row[2]:
                    st.write("**Direction:**")
                    dir_cols = st.columns(2)
                    with dir_cols[0]:
                        upwind = st.checkbox("⬆️ Upwind", value=st.session_state.filter_changes['upwind_selected'], key="upwind_check")
                        st.session_state.filter_changes['upwind_selected'] = upwind
                    with dir_cols[1]:
                        downwind = st.checkbox("⬇️ Downwind", value=st.session_state.filter_changes['downwind_selected'], key="downwind_check")
                        st.session_state.filter_changes['downwind_selected'] = downwind
                
                # Quality filter controls
                with top_row[3]:
                    st.write("**Quality:**")
                    qual_cols = st.columns(2)
                    with qual_cols[0]:
                        no_suspicious = st.checkbox("⚠️ No Suspicious", value=st.session_state.filter_changes['suspicious_removed'], key="suspicious_check")
                        st.session_state.filter_changes['suspicious_removed'] = no_suspicious
                    with qual_cols[1]:
                        fastest = st.checkbox("⚡ Fastest Only", value=st.session_state.filter_changes['best_speed_selected'], key="speed_check")
                        st.session_state.filter_changes['best_speed_selected'] = fastest
                
                # Apply button
                with top_row[4]:
                    st.write("&nbsp;")  # Add some spacing
                    apply_button = st.button("✅ Apply", type="primary", key="apply_filters", use_container_width=True, help="Apply filters & recalculate metrics")
                
                # Second row for status and wind estimation
                bottom_row = filter_container.columns([2, 1])
                
                # Apply all filters together to get the correct selection
                all_segments = display_df['original_index'].tolist()
                filtered_segments = all_segments.copy()
                
                # Initialize filter text in this scope only
                filter_text = []
                
                # Apply direction filters if active
                if st.session_state.filter_changes['upwind_selected'] and not st.session_state.filter_changes['downwind_selected']:
                    upwind_segments = display_df[display_df['upwind_downwind'] == 'Upwind']['original_index'].tolist()
                    filtered_segments = [s for s in filtered_segments if s in upwind_segments]
                    filter_text.append("Upwind only")
                elif st.session_state.filter_changes['downwind_selected'] and not st.session_state.filter_changes['upwind_selected']:
                    downwind_segments = display_df[display_df['upwind_downwind'] == 'Downwind']['original_index'].tolist()
                    filtered_segments = [s for s in filtered_segments if s in downwind_segments]
                    filter_text.append("Downwind only")
                elif st.session_state.filter_changes['upwind_selected'] and st.session_state.filter_changes['downwind_selected']:
                    filter_text.append("All directions")
                
                # Apply suspicious filter if active
                if st.session_state.filter_changes['suspicious_removed']:
                    suspicious_segments = display_df[display_df['suspicious']]['original_index'].tolist()
                    if suspicious_segments:
                        filtered_segments = [s for s in filtered_segments if s not in suspicious_segments]
                    filter_text.append("No suspicious angles")
                
                # Apply speed filter if active
                if st.session_state.filter_changes['best_speed_selected']:
                    speed_threshold = display_df['speed (knots)'].quantile(0.75)
                    fast_segments = display_df[display_df['speed (knots)'] >= speed_threshold]['original_index'].tolist()
                    filtered_segments = [s for s in filtered_segments if s in fast_segments]
                    filter_text.append(f"Fastest (>{speed_threshold:.1f} knots)")
                
                # Update the selected segments
                st.session_state.selected_segments = filtered_segments
                
                # Display filter status in the first column of the bottom row
                with bottom_row[0]:
                    if filter_text:
                        st.info(f"**Active filters:** {', '.join(filter_text)}")
                    else:
                        st.info("**No filters active** - showing all segments")
                
                # Add wind estimation button in the second column
                with bottom_row[1]:
                    # Get the filtered segments for estimation
                    if filtered_segments and len(filtered_segments) > 0:
                        estimation_stretches = stretches.loc[stretches.index.isin(filtered_segments)]
                        segment_count = len(estimation_stretches)
                    else:
                        estimation_stretches = stretches
                        segment_count = len(stretches)
                    
                    # Add wind re-estimation button
                    if st.button("🧭 Re-estimate Wind", help="Recalculate wind direction based on current segments", key="reestimate_wind", use_container_width=True):
                        if segment_count >= 3:  # Need at least 3 segments for reliable estimation
                            # Import here to avoid scope issues
                            from utils.analysis import estimate_wind_direction, estimate_wind_direction_from_upwind_tacks
                            
                            # First try the new upwind tack analysis method
                            # This requires angles to be calculated with some initial wind direction 
                            # We use the current wind direction for this initial calculation
                            current_wind = st.session_state.wind_direction
                            
                            # Calculate angles to wind using current wind direction
                            temp_stretches = analyze_wind_angles(estimation_stretches, current_wind)
                            
                            # Try to estimate using the new tack-based method first
                            # Pass the suspicious angle threshold from user settings
                            new_wind_estimate = estimate_wind_direction_from_upwind_tacks(
                                temp_stretches,
                                suspicious_angle_threshold=suspicious_angle_threshold
                            )
                            
                            # If that fails, fall back to the regular method
                            if new_wind_estimate is None:
                                new_wind_estimate = estimate_wind_direction(estimation_stretches, use_simple_method=True)
                                method_used = "standard clustering"
                            else:
                                method_used = "upwind tack analysis"
                            
                            if new_wind_estimate is not None:
                                st.session_state.estimated_wind = new_wind_estimate
                                st.session_state.wind_direction = new_wind_estimate
                                st.success(f"✅ Wind direction re-estimated: {new_wind_estimate:.1f}° based on your {segment_count} selected segments")
                                
                                # Also recalculate angles with new wind direction
                                # Use the global analyze_wind_angles function
                                if st.session_state.track_stretches is not None:
                                    recalculated = analyze_wind_angles(stretches, new_wind_estimate)
                                    st.session_state.track_stretches = recalculated
                                
                                # Force a rerun to update all calculations with new wind direction
                                st.rerun()
                            else:
                                st.error("⚠️ Couldn't estimate wind direction from selected segments")
                        else:
                            st.warning(f"⚠️ Need at least 3 segments to estimate wind direction. You have {segment_count} selected.")
                
                # Display the map after segment selection
                st.subheader("Track Map")
                display_track_map(gpx_data, stretches, wind_direction, estimated_wind)
                
                # Apply immediately when button is clicked
                # Make sure we trigger a complete recalculation
                if apply_button:
                    # Force recalculation with current wind direction before rerun
                    # This is the key fix to ensure filters and wind direction changes affect all visualizations
                    if st.session_state.track_stretches is not None:
                        # Get the base stretches before wind angle calculation
                        base_stretches = st.session_state.track_stretches.copy()
                        # Use the global analyze_wind_angles function
                        # Recalculate wind angles with current wind direction
                        recalculated_stretches = analyze_wind_angles(base_stretches, wind_direction)
                        # Update session state with fresh calculation
                        st.session_state.track_stretches = recalculated_stretches
                    
                    # Now trigger a full page rerun with the updated data
                    st.rerun()
                
                # Reorganize for a more compact, dense layout with 2 columns for main content
                col1, col2 = st.columns([1, 1])
                
                # LEFT COLUMN - Performance Analysis 
                with col1:
                    # PERFORMANCE ANALYSIS - Best Angles Section
                    st.subheader("📊 Performance Analysis")
                    
                    # Get the filtered segments for analysis
                    if ('selected_segments' in st.session_state and 
                        isinstance(st.session_state.selected_segments, list) and 
                        len(st.session_state.selected_segments) > 0):
                        
                        analysis_stretches = stretches.loc[stretches.index.isin(st.session_state.selected_segments)]
                    else:
                        analysis_stretches = stretches
                    
                    # Find the best angles and speeds
                    if not analysis_stretches.empty:
                        # Split into upwind/downwind for analysis
                        upwind = analysis_stretches[analysis_stretches['angle_to_wind'] < 90]
                        downwind = analysis_stretches[analysis_stretches['angle_to_wind'] >= 90]
                        
                        with st.container(border=True):
                            best_cols = st.columns(2)
                            
                            # UPWIND PERFORMANCE - Best angles/speeds
                            with best_cols[0]:
                                st.markdown("#### 🔼 Best Upwind")
                                if not upwind.empty:
                                    # Split by tack
                                    port_upwind = upwind[upwind['tack'] == 'Port']
                                    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
                                    
                                    # Find best port tack upwind angle
                                    if not port_upwind.empty:
                                        best_port = port_upwind.loc[port_upwind['angle_to_wind'].idxmin()]
                                        st.metric("Best Port Angle", f"{best_port['angle_to_wind']:.1f}°", 
                                                f"{best_port['speed']:.1f} knots")
                                        st.caption(f"Bearing: {best_port['bearing']:.0f}°")
                                    
                                    # Find best starboard tack upwind angle
                                    if not starboard_upwind.empty:
                                        best_starboard = starboard_upwind.loc[starboard_upwind['angle_to_wind'].idxmin()]
                                        st.metric("Best Starboard Angle", f"{best_starboard['angle_to_wind']:.1f}°", 
                                                f"{best_starboard['speed']:.1f} knots")
                                        st.caption(f"Bearing: {best_starboard['bearing']:.0f}°")
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
                    else:
                        st.info("Not enough data for polar plot (need at least 3 segments)")
                    
                    # Polar diagram visualization is enough here
                
                # Create tabs only for secondary detailed data
                tab1, tab2 = st.tabs(["🔍 Segment Data", "📋 Advanced Selection"])
                
                with tab1:
                    # Display segment data table in a compact format
                    # Use only the selected segments for display
                    if ('selected_segments' in st.session_state and 
                        isinstance(st.session_state.selected_segments, list) and 
                        len(st.session_state.selected_segments) > 0):
                        
                        filtered_display_df = display_df[display_df['original_index'].isin(st.session_state.selected_segments)]
                        source_note = f"Showing {len(filtered_display_df)} selected segments"
                    else:
                        filtered_display_df = display_df
                        source_note = f"Showing all {len(display_df)} segments"
                    
                    # Download buttons section
                    st.caption(source_note)
                    cols = st.columns([1, 1])
                    with cols[0]:
                        # Compact download buttons
                        csv = filtered_display_df.to_csv(index=False)
                        st.download_button(
                            "📥 Download Selected Segments (CSV)",
                            data=csv,
                            file_name="wingfoil_segments.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with cols[1]:
                        # Full data export
                        st.download_button(
                            "📊 Download Complete Analysis",
                            data=stretches.to_csv(index=False),
                            file_name="wingfoil_full_analysis.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
                    # Show the filtered dataframe with improved formatting
                    display_cols = [
                        'segment_id', 'sailing_type', 'heading (°)', 
                        'angle off wind (°)', 'speed (knots)', 
                        'distance (m)', 'duration (sec)'
                    ]
                    
                    if not filtered_display_df.empty:
                        # Mark suspicious segments with a symbol instead of styling to avoid errors
                        if 'suspicious' in filtered_display_df.columns:
                            filtered_display_df['sailing_type'] = filtered_display_df.apply(
                                lambda row: f"{row['sailing_type']} ⚠️" if row['suspicious'] else row['sailing_type'], 
                                axis=1
                            )
                        
                        st.dataframe(filtered_display_df[display_cols], use_container_width=True, height=200)
                        st.caption(f"⚠️ indicates suspicious angles (< {suspicious_angle_threshold}°)")
                    else:
                        st.warning("No segments selected. Please use the filters to select segments.")
                
                with tab2:
                    # Advanced segment selection UI with checkboxes - more compact version
                    segment_cols = st.columns([1, 3])
                    
                    with segment_cols[0]:
                        st.info("**Select specific segments using the checkboxes →**")
                        
                        # Add a refresh button to apply segment selection changes
                        apply_selection = st.button("✅ Apply Selection", 
                                               key="apply_segment_selection", 
                                               type="primary",
                                               help="Apply your segment selection changes",
                                               use_container_width=True)
                    
                    with segment_cols[1]:
                        # Group by sailing type for better organization
                        segment_types = display_df['sailing_type'].unique()
                        
                        for sailing_type in segment_types:
                            st.write(f"**{sailing_type}:**")
                            
                            # Get segments of this type
                            type_segments = display_df[display_df['sailing_type'] == sailing_type]
                            
                            # Show in 4 columns for more density
                            check_cols = st.columns(4)
                            
                            # Distribute segments across columns
                            segments_per_col = len(type_segments) // 4 + 1
                            
                            col_idx = 0
                            segment_count = 0
                            
                            for i, row in type_segments.iterrows():
                                segment_id = row['original_index']  # Use original index for selection
                                angle = row['angle off wind (°)']
                                speed = row['speed (knots)']
                                is_suspicious = row['suspicious']
                                
                                # Switch to next column if needed
                                if segment_count >= segments_per_col:
                                    col_idx = (col_idx + 1) % 4
                                    segment_count = 0
                                
                                # Format the label based on whether it's suspicious - more compact
                                label = f"#{int(row['segment_id'])}: {angle}°" + ("⚠️" if is_suspicious else "")
                                
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
                    
                    if apply_selection:
                        st.rerun()
                        
                # Add average angles at the bottom after all tabs
                if ('selected_segments' in st.session_state and 
                    isinstance(st.session_state.selected_segments, list) and 
                    len(st.session_state.selected_segments) > 0):
                    filtered_stretches = stretches.loc[stretches.index.isin(st.session_state.selected_segments)]
                else:
                    filtered_stretches = stretches
                
                if len(filtered_stretches) > 0:
                    from utils.calculations import calculate_average_angle_from_segments
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
                st.warning("No segments meet minimum speed criteria.")
        else:
            st.warning("No consistent angle segments found. Try adjusting parameters.")
    else:
        if uploaded_file is not None:
            st.error("Unable to parse GPX data. Check file format.")

if __name__ == "__main__":
    main()