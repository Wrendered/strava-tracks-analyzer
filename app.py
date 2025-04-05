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
        
        # Wind direction input
        wind_direction = st.number_input("Wind Direction (°)", 
                                        min_value=0, max_value=359, value=90,
                                        help="Direction the wind is coming FROM")
        
        angle_tolerance = st.slider("Angle Tolerance (°)", 
                                    min_value=1, max_value=20, value=10)
        
        # Minimum criteria
        min_duration = st.slider("Min Duration (sec)", min_value=1, max_value=60, value=10)
        min_distance = st.slider("Min Distance (m)", min_value=10, max_value=200, value=50)
        min_speed = st.slider("Min Speed (knots)", min_value=5.0, max_value=30.0, value=10.0, step=0.5)

        min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
        
        # Advanced options
        st.subheader("Advanced")
        auto_detect_wind = st.checkbox("Auto-detect wind direction", value=True)
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
                        # Try to estimate wind direction if requested
                        if auto_detect_wind:
                            try:
                                estimated_wind = estimate_wind_direction(stretches, use_simple_method=use_simple_method)
                                if estimated_wind is not None:
                                    logger.info(f"Estimated wind direction: {estimated_wind:.1f}° (using {'simple' if use_simple_method else 'complex'} method)")
                                    st.sidebar.success(f"Estimated wind direction: {estimated_wind:.1f}°")
                                    if st.sidebar.button("Use Estimated Wind"):
                                        wind_direction = estimated_wind
                                        logger.info(f"Using estimated wind direction: {wind_direction:.1f}°")
                                        st.experimental_rerun()
                                else:
                                    logger.warning("Could not estimate wind direction")
                            except Exception as e:
                                logger.error(f"Error estimating wind direction: {e}")
                                estimated_wind = None
                        else:
                            estimated_wind = None

                        
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
                                        st.metric("Best Port Upwind", 
                                                f"{best_port['angle_to_wind']:.1f}°", 
                                                f"{best_port['speed']:.1f} knots")
                                    
                                    if not starboard.empty:
                                        best_stbd = starboard.loc[starboard['angle_to_wind'].idxmin()]
                                        st.metric("Best Starboard Upwind", 
                                                f"{best_stbd['angle_to_wind']:.1f}°", 
                                                f"{best_stbd['speed']:.1f} knots")
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
                                        st.metric("Best Port Downwind", 
                                                f"{best_port['angle_to_wind']:.1f}°", 
                                                f"{best_port['speed']:.1f} knots")
                                    
                                    if not starboard.empty:
                                        best_stbd = starboard.loc[starboard['angle_to_wind'].idxmax()]
                                        st.metric("Best Starboard Downwind", 
                                                f"{best_stbd['angle_to_wind']:.1f}°", 
                                                f"{best_stbd['speed']:.1f} knots")
                                else:
                                    st.info("No downwind data detected")
                        
                        # Plot bearing distribution
                        st.subheader("Bearing Distribution")
                        fig = plot_bearing_distribution(stretches, wind_direction)
                        st.pyplot(fig)
                        
                        # Display data table
                        st.subheader(f"Detected Segments ({len(stretches)})")
                        display_cols = ['sailing_type', 'bearing', 'angle_to_wind', 
                                      'distance', 'speed', 'duration']
                        display_df = stretches[display_cols].copy()
                        
                        # Format for display
                        for col in ['bearing', 'angle_to_wind']:
                            display_df[col] = display_df[col].round(1)
                        display_df['distance'] = display_df['distance'].round(1)
                        display_df['speed'] = display_df['speed'].round(2)
                        
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