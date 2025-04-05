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
    st.set_page_config(layout="wide", page_title="Wingfoil Track Analyzer")
    
    st.title("Wingfoil Track Analyzer")
    st.markdown("Analyze your wingfoil tracks to improve performance")
    
    logger.info("App started")
    
    # Sidebar parameters
    with st.sidebar:
        st.header("Analysis Parameters")
        
        # Wind direction section
        st.subheader("Wind Direction")
        wind_mode = st.radio(
            "Wind Direction Mode",
            ["Manual", "Auto-detect"], 
            index=0,
            horizontal=True
        )
        
        # Wind direction input or display
        if wind_mode == "Manual":
            wind_direction = st.number_input(
                "Wind Direction (°)", 
                min_value=0, 
                max_value=359, 
                value=90,
                help="Direction the wind is coming FROM (0-359°)"
            )
            auto_detect_wind = False
        else:
            st.info("Wind direction will be automatically estimated from your track data")
            wind_direction = 90  # Default value if auto-detection fails
            auto_detect_wind = True
            
            # Add manual override option
            if st.checkbox("Show manual override", value=False):
                manual_wind = st.number_input(
                    "Override Wind Direction (°)", 
                    min_value=0, 
                    max_value=359, 
                    value=wind_direction
                )
                if st.button("Use Override Value"):
                    wind_direction = manual_wind
                    auto_detect_wind = False
        
        # Segment detection parameters
        st.subheader("Segment Detection")
        angle_tolerance = st.slider("Angle Tolerance (°)", 
                                   min_value=1, max_value=20, value=10)
        
        # Minimum criteria
        min_duration = st.slider("Min Duration (sec)", min_value=1, max_value=60, value=10)
        min_distance = st.slider("Min Distance (m)", min_value=10, max_value=200, value=50)
        min_speed = st.slider("Min Speed (knots)", min_value=5.0, max_value=30.0, value=10.0, step=0.5)

        min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
        
        # Advanced options
        st.subheader("Advanced Options")
        advanced_mode = st.checkbox("Advanced Mode", value=False, 
                                   help="Enable advanced features and options")
        
        if advanced_mode:
            wind_estimation_method = st.radio(
                "Wind Estimation Method",
                ["Simple", "Complex"],
                index=0,
                help="Simple works better for real data, complex for synthetic data"
            )
            use_simple_method = wind_estimation_method == "Simple"
        else:
            use_simple_method = True  # Default to simple method
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a GPX file", type=['gpx'])
    
    if uploaded_file is not None:
        logger.info(f"Processing uploaded file: {uploaded_file.name}")
        with st.spinner("Processing GPX data..."):
            # Load GPX data
            try:
                gpx_data = load_gpx_file(uploaded_file)
                logger.info(f"Loaded GPX file with {len(gpx_data)} points")
            except Exception as e:
                logger.error(f"Error loading GPX file: {e}")
                st.error(f"Error loading GPX file: {e}")
                gpx_data = pd.DataFrame()
            
            # Calculate basic track metrics
            if not gpx_data.empty:
                metrics = calculate_track_metrics(gpx_data)
                
                # Display track summary
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Track Summary")
                    st.write(f"📅 Date: {metrics['date']}")
                    st.write(f"⏱️ Duration: {metrics['duration']}")
                
                with col2:
                    st.metric("📏 Total Distance", f"{metrics['distance']:.2f} km")
                    st.metric("⚡ Average Speed", f"{metrics['avg_speed']:.2f} knots")
                
                # Find consistent angle stretches
                stretches = find_consistent_angle_stretches(
                    gpx_data, angle_tolerance, min_duration, min_distance
                )
                
                if not stretches.empty:
                    # Filter by minimum speed
                    stretches = stretches[stretches['speed'] >= min_speed_ms]
                    
                    if not stretches.empty:
                        # Always try to estimate wind direction for comparison
                        estimated_wind = None
                        try:
                            estimated_wind = estimate_wind_direction(stretches, use_simple_method=use_simple_method)
                            if estimated_wind is not None:
                                logger.info(f"Estimated wind direction: {estimated_wind:.1f}° (using {'simple' if use_simple_method else 'complex'} method)")
                                
                                # If auto-detect is on, use the estimated wind
                                if auto_detect_wind:
                                    # Display success and use the estimated value
                                    wind_direction = estimated_wind
                                    st.sidebar.success(f"Using estimated wind direction: {estimated_wind:.1f}°")
                                    
                                    # Offer option to adjust the estimated wind
                                    with st.sidebar:
                                        adjusted_wind = st.slider(
                                            "Fine-tune Wind Direction", 
                                            min_value=max(0, int(estimated_wind) - 20),
                                            max_value=min(359, int(estimated_wind) + 20),
                                            value=int(estimated_wind)
                                        )
                                        if adjusted_wind != int(estimated_wind):
                                            wind_direction = adjusted_wind
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
                        
                        # Display visualization and analysis
                        col1, col2 = st.columns(2)
                        
                        # When displaying the map, pass the estimated wind:
                        with col1:
                            # Display map
                            st.subheader("Track Map")
                            display_track_map(gpx_data, stretches, wind_direction, estimated_wind)
                        
                        with col2:
                            # Display polar plot
                            st.subheader("Polar Performance")
                            if len(stretches) > 2:
                                fig = plot_polar_diagram(stretches, wind_direction)
                                st.pyplot(fig)
                            else:
                                st.info("Not enough data for polar plot")
                        
                        # Display explanation of angles
                        st.subheader("Wind Angle Explanation")
                        st.markdown("""
                        The angles shown below are measured as **degrees off the wind direction**:
                        - **0°** means sailing directly into the wind (impossible)
                        - **45°** is a typical upwind angle
                        - **90°** is sailing across the wind (beam reach)
                        - **180°** is sailing directly downwind
                        
                        Smaller angles are better for upwind performance, larger angles are better for downwind.
                        """)
                        
                        # Display upwind/downwind analysis
                        st.subheader("Wind Angle Analysis")
                        upwind = stretches[stretches['angle_to_wind'] < 90]
                        downwind = stretches[stretches['angle_to_wind'] >= 90]
                        
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
                                    st.info("No upwind data detected")
                            
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
                                    st.info("No downwind data detected")
                        
                        # Plot bearing distribution
                        st.subheader("Bearing Distribution")
                        fig = plot_bearing_distribution(stretches, wind_direction)
                        st.pyplot(fig)
                        
                        # Display data table
                        st.subheader(f"Detected Segments ({len(stretches)})")
                        
                        # Create a DataFrame with renamed columns for clarity
                        display_cols = ['sailing_type', 'bearing', 'angle_to_wind', 
                                      'distance', 'speed', 'duration']
                        
                        display_df = stretches[display_cols].copy()
                        
                        # Rename columns to be clearer
                        display_df = display_df.rename(columns={
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
                        
                        st.dataframe(display_df)
                        
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
                st.error("Unable to parse GPX data. Check file format.")

if __name__ == "__main__":
    main()