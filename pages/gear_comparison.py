import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../app.log'))
    ]
)
logger = logging.getLogger(__name__)

from utils.gpx_parser import load_gpx_file
from utils.calculations import calculate_track_metrics
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles, estimate_wind_direction
from utils.visualization import plot_bearing_distribution, plot_polar_diagram


def create_side_by_side_polars(gear1_stretches, gear2_stretches, gear1_name, gear2_name, wind_direction1, wind_direction2):
    """Create side-by-side polar plots for comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), subplot_kw={'projection': 'polar'})
    
    plt.suptitle(f"Gear Comparison: {gear1_name} vs {gear2_name}", fontsize=16)
    
    # Plot Gear 1 on the left
    plot_gear_polar(ax1, gear1_stretches, gear1_name, wind_direction1)
    
    # Plot Gear 2 on the right
    plot_gear_polar(ax2, gear2_stretches, gear2_name, wind_direction2)
    
    # Add explanatory text with better spacing
    plt.figtext(0.5, 0.01, 
               "These polar plots show speed (radius) at different angles to the wind.\n" +
               "0° is directly into the wind (top), 90° is across (sides), 180° is directly downwind (bottom).\n" +
               "Marker size indicates distance sailed at this angle/speed combination.",
               ha='center', fontsize=9, wrap=True)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    
    return fig


def plot_gear_polar(ax, stretches, gear_name, wind_direction):
    """Plot a polar diagram for a single gear on the given axis."""
    if stretches.empty:
        ax.set_title(f"{gear_name}: No data", fontweight='bold', pad=15)
        return
    
    # Get data ready
    port_mask = stretches['tack'] == 'Port'
    starboard_mask = stretches['tack'] == 'Starboard'
    
    # Create a colormap for upwind/downwind
    cmap = plt.cm.coolwarm
    
    max_speeds = []
    
    # Plot PORT tack data
    if sum(port_mask) > 0:
        port_data = stretches[port_mask].copy()
        
        # Get values
        thetas = np.radians(port_data['angle_to_wind'].values)
        r = port_data['speed'].values  # Speed in knots
        weights = port_data['distance'].values
        max_speeds.append(max(r) if len(r) > 0 else 0)
        
        # Normalize weights for scatter size
        norm_weights = 20 * weights / weights.max() + 10 if weights.max() > 0 else 10
        
        # Plot the port tack points
        ax.scatter(
            thetas, r, 
            c=port_data['angle_to_wind'], 
            cmap=cmap, s=norm_weights, alpha=0.8, 
            vmin=0, vmax=180, marker='o'
        )
    
    # Plot STARBOARD tack data
    if sum(starboard_mask) > 0:
        starboard_data = stretches[starboard_mask].copy()
        
        # Get values
        thetas = np.radians(starboard_data['angle_to_wind'].values)
        r = starboard_data['speed'].values  # Speed in knots
        weights = starboard_data['distance'].values
        max_speeds.append(max(r) if len(r) > 0 else 0)
        
        # Normalize weights for scatter size
        norm_weights = 20 * weights / weights.max() + 10 if weights.max() > 0 else 10
        
        # Plot the starboard tack points
        ax.scatter(
            thetas, r, 
            c=starboard_data['angle_to_wind'], 
            cmap=cmap, s=norm_weights, alpha=0.8, 
            vmin=0, vmax=180, marker='s'
        )
    
    # Set up the polar plot
    ax.set_theta_zero_location('N')  # 0 degrees at the top
    ax.set_theta_direction(-1)  # clockwise
    
    # Set the theta limits to 0-180 degrees (only show the top half)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    
    # Get max speed and set consistent scaling
    if max_speeds:
        max_r = max(max_speeds)
        
        # Set consistent speed rings
        radii = np.linspace(0, np.ceil(max_r), 6)
        ax.set_rticks(radii)
        ax.set_rlim(0, np.ceil(max_r) * 1.1)
        
        # Add important angle reference lines
        angles = [0, 45, 90, 135, 180]
        labels = ["0°", "45°", "90°", "135°", "180°"]
        linestyles = [':', '--', '-', '--', ':']
        colors = ['black', 'red', 'green', 'orange', 'black']
        
        for angle, label, ls, color in zip(angles, labels, linestyles, colors):
            # Add radial lines at important angles
            ax.plot([np.radians(angle), np.radians(angle)], [0, max_r * 1.1], 
                    ls=ls, color=color, alpha=0.5, linewidth=1)
            
            # Add angle labels just outside the plot
            ax.text(np.radians(angle), max_r * 1.07, label, 
                    ha='center', va='center', color=color, fontsize=9)
    
    # Add legend for port/starboard
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='grey', markersize=8, label='Port'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='grey', markersize=8, label='Starboard')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    # Add title with gear name and wind direction
    ax.set_title(f"{gear_name}\nWind: {wind_direction}°", fontweight='bold', pad=15)


def create_polar_comparison_section(stretches1, stretches2, gear1_name, gear2_name, wind_direction1, wind_direction2):
    """Create a comparative analysis section with polar plot and statistics."""
    if stretches1.empty or stretches2.empty:
        st.warning("Need data for both gear types to perform comparison")
        return
    
    # Add key headline stats at the top
    st.write("### Key Performance Highlights")
    
    # Calculate headline metrics
    headline_metrics = calculate_headline_metrics(stretches1, stretches2, gear1_name, gear2_name)
    
    # Display headline metrics in 4 columns
    cols = st.columns(4)
    
    with cols[0]:  # Upwind Angle
        better_upwind = headline_metrics['better_upwind']
        st.metric(
            "Better Upwind",
            f"{better_upwind['name']}",
            f"{better_upwind['angle']:.1f}° to wind",
            help="Gear that points closer to the wind (smaller angle is better for upwind)"
        )
    
    with cols[1]:  # Upwind Speed
        faster_upwind = headline_metrics['faster_upwind']
        st.metric(
            "Faster Upwind",
            f"{faster_upwind['name']}",
            f"{faster_upwind['speed']:.1f} knots",
            help="Gear with higher average speed when sailing upwind"
        )
    
    with cols[2]:  # Downwind Angle
        better_downwind = headline_metrics['better_downwind']
        st.metric(
            "Better Downwind",
            f"{better_downwind['name']}",
            f"{better_downwind['angle']:.1f}° to wind",
            help="Gear that sails deeper downwind (larger angle is better for downwind)"
        )
        
    with cols[3]:  # Downwind Speed
        faster_downwind = headline_metrics['faster_downwind']
        st.metric(
            "Faster Downwind",
            f"{faster_downwind['name']}",
            f"{faster_downwind['speed']:.1f} knots",
            help="Gear with higher average speed when sailing downwind"
        )
    
    # Plot the comparative polar diagram
    st.write("### Polar Performance Comparison")
    fig = create_side_by_side_polars(
        stretches1, stretches2, gear1_name, gear2_name, wind_direction1, wind_direction2
    )
    st.pyplot(fig)
    
    # Extract upwind/downwind metrics for both gear types
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"#### {gear1_name} Performance Metrics")
        create_gear_metrics_table(stretches1)
        
    with col2:
        st.write(f"#### {gear2_name} Performance Metrics") 
        create_gear_metrics_table(stretches2)
    
    # Show direct comparisons between the two gear types
    st.write("### Head-to-Head Comparison")
    create_comparison_table(stretches1, stretches2, gear1_name, gear2_name)


def calculate_headline_metrics(stretches1, stretches2, gear1_name, gear2_name):
    """Calculate headline metrics for the comparison summary."""
    # Split data into upwind and downwind
    upwind1 = stretches1[stretches1['angle_to_wind'] < 90]
    upwind2 = stretches2[stretches2['angle_to_wind'] < 90]
    downwind1 = stretches1[stretches1['angle_to_wind'] >= 90]
    downwind2 = stretches2[stretches2['angle_to_wind'] >= 90]
    
    results = {}
    
    # Compare upwind angle performance (smaller is better)
    if not upwind1.empty and not upwind2.empty:
        min_angle1 = upwind1['angle_to_wind'].min()
        min_angle2 = upwind2['angle_to_wind'].min()
        
        if min_angle1 <= min_angle2:
            results['better_upwind'] = {
                'name': gear1_name,
                'angle': min_angle1
            }
        else:
            results['better_upwind'] = {
                'name': gear2_name,
                'angle': min_angle2
            }
    elif not upwind1.empty:
        results['better_upwind'] = {
            'name': gear1_name,
            'angle': upwind1['angle_to_wind'].min()
        }
    elif not upwind2.empty:
        results['better_upwind'] = {
            'name': gear2_name,
            'angle': upwind2['angle_to_wind'].min()
        }
    else:
        results['better_upwind'] = {
            'name': "No data",
            'angle': 0.0
        }
    
    # Compare upwind speed performance (higher is better)
    if not upwind1.empty and not upwind2.empty:
        avg_speed1 = upwind1['speed'].mean()
        avg_speed2 = upwind2['speed'].mean()
        
        if avg_speed1 >= avg_speed2:
            results['faster_upwind'] = {
                'name': gear1_name,
                'speed': avg_speed1
            }
        else:
            results['faster_upwind'] = {
                'name': gear2_name,
                'speed': avg_speed2
            }
    elif not upwind1.empty:
        results['faster_upwind'] = {
            'name': gear1_name,
            'speed': upwind1['speed'].mean()
        }
    elif not upwind2.empty:
        results['faster_upwind'] = {
            'name': gear2_name,
            'speed': upwind2['speed'].mean()
        }
    else:
        results['faster_upwind'] = {
            'name': "No data",
            'speed': 0.0
        }
    
    # Compare downwind angle performance (larger is better)
    if not downwind1.empty and not downwind2.empty:
        max_angle1 = downwind1['angle_to_wind'].max()
        max_angle2 = downwind2['angle_to_wind'].max()
        
        if max_angle1 >= max_angle2:
            results['better_downwind'] = {
                'name': gear1_name,
                'angle': max_angle1
            }
        else:
            results['better_downwind'] = {
                'name': gear2_name,
                'angle': max_angle2
            }
    elif not downwind1.empty:
        results['better_downwind'] = {
            'name': gear1_name,
            'angle': downwind1['angle_to_wind'].max()
        }
    elif not downwind2.empty:
        results['better_downwind'] = {
            'name': gear2_name,
            'angle': downwind2['angle_to_wind'].max()
        }
    else:
        results['better_downwind'] = {
            'name': "No data",
            'angle': 0.0
        }
    
    # Compare downwind speed performance (higher is better)
    if not downwind1.empty and not downwind2.empty:
        avg_speed1 = downwind1['speed'].mean()
        avg_speed2 = downwind2['speed'].mean()
        
        if avg_speed1 >= avg_speed2:
            results['faster_downwind'] = {
                'name': gear1_name,
                'speed': avg_speed1
            }
        else:
            results['faster_downwind'] = {
                'name': gear2_name,
                'speed': avg_speed2
            }
    elif not downwind1.empty:
        results['faster_downwind'] = {
            'name': gear1_name,
            'speed': downwind1['speed'].mean()
        }
    elif not downwind2.empty:
        results['faster_downwind'] = {
            'name': gear2_name,
            'speed': downwind2['speed'].mean()
        }
    else:
        results['faster_downwind'] = {
            'name': "No data",
            'speed': 0.0
        }
    
    return results


def create_gear_metrics_table(stretches):
    """Create a metrics table for a single gear type."""
    if stretches.empty:
        st.info("No data available")
        return
    
    # Split by upwind/downwind
    upwind = stretches[stretches['angle_to_wind'] < 90]
    downwind = stretches[stretches['angle_to_wind'] >= 90]
    
    # Calculate metrics
    metrics = {}
    
    # Overall
    metrics["Overall Max Speed"] = f"{stretches['speed'].max():.1f} knots"
    metrics["Overall Avg Speed"] = f"{stretches['speed'].mean():.1f} knots"
    
    # Upwind
    if not upwind.empty:
        best_upwind_speed_idx = upwind['speed'].idxmax()
        max_upwind_speed = upwind.loc[best_upwind_speed_idx, 'speed']
        angle_at_max_speed = upwind.loc[best_upwind_speed_idx, 'angle_to_wind']
        
        min_upwind_angle = upwind['angle_to_wind'].min()
        min_angle_idx = upwind['angle_to_wind'].idxmin()
        speed_at_min_angle = upwind.loc[min_angle_idx, 'speed']
        
        # Formatted metrics
        metrics["Upwind - Best Pointing"] = f"{min_upwind_angle:.1f}° to wind ({speed_at_min_angle:.1f} knots)"
        metrics["Upwind - Fastest"] = f"{max_upwind_speed:.1f} knots (at {angle_at_max_speed:.1f}° to wind)"
        metrics["Upwind - Avg Speed"] = f"{upwind['speed'].mean():.1f} knots"
    
    # Downwind
    if not downwind.empty:
        best_downwind_speed_idx = downwind['speed'].idxmax()
        max_downwind_speed = downwind.loc[best_downwind_speed_idx, 'speed']
        angle_at_max_speed = downwind.loc[best_downwind_speed_idx, 'angle_to_wind']
        
        max_downwind_angle = downwind['angle_to_wind'].max()
        max_angle_idx = downwind['angle_to_wind'].idxmax()
        speed_at_max_angle = downwind.loc[max_angle_idx, 'speed']
        
        # Formatted metrics
        metrics["Downwind - Deepest Run"] = f"{max_downwind_angle:.1f}° to wind ({speed_at_max_angle:.1f} knots)"
        metrics["Downwind - Fastest"] = f"{max_downwind_speed:.1f} knots (at {angle_at_max_speed:.1f}° to wind)"
        metrics["Downwind - Avg Speed"] = f"{downwind['speed'].mean():.1f} knots"
    
    # Create a DataFrame for display
    df = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
    
    # Add section headers for clarity
    section_indices = {}
    if "Overall Max Speed" in metrics:
        section_indices["OVERALL"] = 0
    
    if "Upwind - Best Pointing" in metrics:
        section_indices["UPWIND"] = df[df["Metric"] == "Upwind - Best Pointing"].index[0]
        
    if "Downwind - Deepest Run" in metrics:
        section_indices["DOWNWIND"] = df[df["Metric"] == "Downwind - Deepest Run"].index[0]
    
    # Display with section headers
    for section, idx in sorted(section_indices.items(), key=lambda x: x[1]):
        st.markdown(f"**{section}**")
        section_end = list(section_indices.values())[list(section_indices.values()).index(idx) + 1] if list(section_indices.values()).index(idx) < len(section_indices) - 1 else len(df)
        st.table(df.iloc[idx:section_end])


def create_comparison_table(stretches1, stretches2, gear1_name, gear2_name):
    """Create a direct comparison table between two gear types."""
    if stretches1.empty or stretches2.empty:
        st.info("Need data for both gear types to perform comparison")
        return
    
    # General comparison
    st.markdown("**Overall Performance**")
    
    # Calculate comparison metrics
    overall_comparison = {}
    
    # Max Speed
    max_speed1 = stretches1['speed'].max()
    max_speed2 = stretches2['speed'].max()
    speed_diff = max_speed1 - max_speed2
    overall_comparison["Maximum Speed"] = [
        f"{max_speed1:.1f} knots", 
        f"{max_speed2:.1f} knots",
        f"{abs(speed_diff):.1f} knots {gear1_name if speed_diff > 0 else gear2_name}"
    ]
    
    # Avg Speed
    avg_speed1 = stretches1['speed'].mean()
    avg_speed2 = stretches2['speed'].mean()
    avg_diff = avg_speed1 - avg_speed2
    overall_comparison["Average Speed"] = [
        f"{avg_speed1:.1f} knots", 
        f"{avg_speed2:.1f} knots",
        f"{abs(avg_diff):.1f} knots {gear1_name if avg_diff > 0 else gear2_name}"
    ]
    
    # Create overall comparison DataFrame
    overall_df = pd.DataFrame.from_dict(
        overall_comparison, 
        orient='index',
        columns=[gear1_name, gear2_name, "Difference (Better Gear)"]
    )
    st.table(overall_df)
    
    # Upwind comparison
    upwind1 = stretches1[stretches1['angle_to_wind'] < 90]
    upwind2 = stretches2[stretches2['angle_to_wind'] < 90]
    
    if not upwind1.empty and not upwind2.empty:
        st.markdown("**Upwind Performance**")
        upwind_comparison = {}
        
        # Best pointing angle
        min_angle1 = upwind1['angle_to_wind'].min()
        min_angle2 = upwind2['angle_to_wind'].min()
        angle_diff = min_angle1 - min_angle2
        upwind_comparison["Best Pointing Angle"] = [
            f"{min_angle1:.1f}°", 
            f"{min_angle2:.1f}°",
            f"{abs(angle_diff):.1f}° {gear2_name if angle_diff > 0 else gear1_name}"
        ]
        
        # Average upwind speed
        avg_upwind_speed1 = upwind1['speed'].mean()
        avg_upwind_speed2 = upwind2['speed'].mean()
        upwind_avg_diff = avg_upwind_speed1 - avg_upwind_speed2
        upwind_comparison["Average Upwind Speed"] = [
            f"{avg_upwind_speed1:.1f} knots", 
            f"{avg_upwind_speed2:.1f} knots",
            f"{abs(upwind_avg_diff):.1f} knots {gear1_name if upwind_avg_diff > 0 else gear2_name}"
        ]
        
        # Maximum upwind speed
        max_upwind_speed1 = upwind1['speed'].max()
        max_upwind_speed2 = upwind2['speed'].max()
        upwind_max_diff = max_upwind_speed1 - max_upwind_speed2
        upwind_comparison["Maximum Upwind Speed"] = [
            f"{max_upwind_speed1:.1f} knots", 
            f"{max_upwind_speed2:.1f} knots",
            f"{abs(upwind_max_diff):.1f} knots {gear1_name if upwind_max_diff > 0 else gear2_name}"
        ]
        
        # Create upwind comparison DataFrame
        upwind_df = pd.DataFrame.from_dict(
            upwind_comparison, 
            orient='index',
            columns=[gear1_name, gear2_name, "Difference (Better Gear)"]
        )
        st.table(upwind_df)
    
    # Downwind comparison
    downwind1 = stretches1[stretches1['angle_to_wind'] >= 90]
    downwind2 = stretches2[stretches2['angle_to_wind'] >= 90]
    
    if not downwind1.empty and not downwind2.empty:
        st.markdown("**Downwind Performance**")
        downwind_comparison = {}
        
        # Deepest downwind angle
        max_angle1 = downwind1['angle_to_wind'].max()
        max_angle2 = downwind2['angle_to_wind'].max()
        max_angle_diff = max_angle1 - max_angle2
        downwind_comparison["Deepest Downwind Angle"] = [
            f"{max_angle1:.1f}°", 
            f"{max_angle2:.1f}°",
            f"{abs(max_angle_diff):.1f}° {gear1_name if max_angle_diff > 0 else gear2_name}"
        ]
        
        # Average downwind speed
        avg_downwind_speed1 = downwind1['speed'].mean()
        avg_downwind_speed2 = downwind2['speed'].mean()
        downwind_avg_diff = avg_downwind_speed1 - avg_downwind_speed2
        downwind_comparison["Average Downwind Speed"] = [
            f"{avg_downwind_speed1:.1f} knots", 
            f"{avg_downwind_speed2:.1f} knots",
            f"{abs(downwind_avg_diff):.1f} knots {gear1_name if downwind_avg_diff > 0 else gear2_name}"
        ]
        
        # Maximum downwind speed
        max_downwind_speed1 = downwind1['speed'].max()
        max_downwind_speed2 = downwind2['speed'].max()
        downwind_max_diff = max_downwind_speed1 - max_downwind_speed2
        downwind_comparison["Maximum Downwind Speed"] = [
            f"{max_downwind_speed1:.1f} knots", 
            f"{max_downwind_speed2:.1f} knots",
            f"{abs(downwind_max_diff):.1f} knots {gear1_name if downwind_max_diff > 0 else gear2_name}"
        ]
        
        # Create downwind comparison DataFrame
        downwind_df = pd.DataFrame.from_dict(
            downwind_comparison, 
            orient='index',
            columns=[gear1_name, gear2_name, "Difference (Better Gear)"]
        )
        st.table(downwind_df)


def process_gpx_file(uploaded_file, angle_tolerance, min_duration, min_distance, min_speed_ms, active_speed_threshold):
    """Process a GPX file and return stretches for analysis with estimated wind direction."""
    try:
        gpx_data = load_gpx_file(uploaded_file)
        logger.info(f"Loaded GPX file with {len(gpx_data)} points")
    except Exception as e:
        logger.error(f"Error loading GPX file: {str(e)}")
        st.error(f"Error loading GPX file: {str(e)}")
        return pd.DataFrame(), None, None
    
    if gpx_data.empty:
        return pd.DataFrame(), None, None
    
    # Calculate basic track metrics
    metrics = calculate_track_metrics(gpx_data, min_speed_knots=active_speed_threshold)
    
    # Find consistent angle stretches
    stretches = find_consistent_angle_stretches(
        gpx_data, angle_tolerance, min_duration, min_distance
    )
    
    if stretches.empty:
        return pd.DataFrame(), None, None
    
    # Filter by minimum speed
    stretches = stretches[stretches['speed'] >= min_speed_ms]
    
    if stretches.empty:
        return pd.DataFrame(), None, None
    
    # Try to estimate wind direction
    try:
        # First with simple method
        estimated_wind = estimate_wind_direction(stretches, use_simple_method=True)
        
        # If that fails, try with complex method
        if estimated_wind is None:
            estimated_wind = estimate_wind_direction(stretches, use_simple_method=False)
        
        # If still no wind direction, use default
        if estimated_wind is None:
            estimated_wind = 90
            wind_message = "Could not estimate wind direction, using default (90°)"
        else:
            wind_message = f"Estimated wind direction: {estimated_wind:.1f}°"
            
    except Exception as e:
        logger.error(f"Error estimating wind direction: {str(e)}")
        estimated_wind = 90
        wind_message = f"Error estimating wind direction: {str(e)}"
    
    # Calculate angles relative to wind
    stretches = analyze_wind_angles(stretches, estimated_wind)
    
    return stretches, metrics, estimated_wind, wind_message


def st_main():
    st.title("Gear Comparison")
    st.markdown("Compare performance between different gear types")
    
    # Common settings for both files
    with st.sidebar:
        st.header("Analysis Parameters")
        
        # Wind direction auto-detection
        st.subheader("Wind Direction")
        wind_autodetect = st.checkbox(
            "Auto-detect Wind Direction (recommended)", 
            value=True,
            help="Automatically estimate wind direction from track data (recommended for comparison)"
        )
        
        # Show the manual wind input if auto-detect is off
        if not wind_autodetect:
            st.warning("Manual wind direction setting not recommended for gear comparison")
            wind_direction = st.number_input(
                "Wind Direction (°)", 
                min_value=0, 
                max_value=359, 
                value=90,
                help="Direction the wind is coming FROM (0-359°)"
            )
        
        # Segment detection parameters
        st.subheader("Segment Detection")
        angle_tolerance = st.slider("Angle Tolerance (°)", 
                                   min_value=5, max_value=20, value=12,
                                   help="How much the bearing can vary within a segment")
        
        # Minimum criteria
        min_duration = st.slider("Min Duration (sec)", min_value=1, max_value=60, value=10)
        min_distance = st.slider("Min Distance (m)", min_value=10, max_value=200, value=50)
        min_speed = st.slider("Min Speed (knots)", min_value=5.0, max_value=30.0, value=10.0, step=0.5)
        min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
        
        st.subheader("Speed Filter")
        active_speed_threshold = st.slider(
            "Active Speed Threshold (knots)", 
            min_value=0.0, max_value=10.0, value=5.0, step=0.5,
            help="Speeds below this will be excluded from average speed calculation"
        )
    
    # Create two columns for file uploads
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Gear 1")
        gear1_name = st.text_input("Gear 1 Name", "5m Wing, 85L Board")
        gear1_file = st.file_uploader("Upload GPX for Gear 1", type=["gpx"])
    
    with col2:
        st.subheader("Gear 2")
        gear2_name = st.text_input("Gear 2 Name", "4m Wing, 90L Board")
        gear2_file = st.file_uploader("Upload GPX for Gear 2", type=["gpx"])
    
    # Process files and create comparison
    if gear1_file and gear2_file:
        with st.spinner("Processing GPX files..."):
            # Process both files
            gear1_result = process_gpx_file(
                gear1_file, angle_tolerance, min_duration, 
                min_distance, min_speed_ms, active_speed_threshold
            )
            
            gear2_result = process_gpx_file(
                gear2_file, angle_tolerance, min_duration,
                min_distance, min_speed_ms, active_speed_threshold
            )
            
            # Unpack results
            if len(gear1_result) == 4:
                gear1_stretches, gear1_metrics, gear1_wind, gear1_wind_msg = gear1_result
            else:
                gear1_stretches, gear1_metrics, gear1_wind = gear1_result
                gear1_wind_msg = "No wind direction detected"
                
            if len(gear2_result) == 4:
                gear2_stretches, gear2_metrics, gear2_wind, gear2_wind_msg = gear2_result
            else:
                gear2_stretches, gear2_metrics, gear2_wind = gear2_result
                gear2_wind_msg = "No wind direction detected"
            
            # Display wind direction messages
            st.info(f"Gear 1 ({gear1_name}): {gear1_wind_msg}")
            st.info(f"Gear 2 ({gear2_name}): {gear2_wind_msg}")
            
            # If manual wind direction was specified
            if not wind_autodetect and 'wind_direction' in locals():
                gear1_wind = wind_direction
                gear2_wind = wind_direction
                st.warning(f"Using manual wind direction: {wind_direction}° for both tracks (not recommended)")
            
            # Display comparison if both files were processed successfully
            if not gear1_stretches.empty and not gear2_stretches.empty:
                create_polar_comparison_section(
                    gear1_stretches, gear2_stretches, 
                    gear1_name, gear2_name, 
                    gear1_wind, gear2_wind
                )
            else:
                if gear1_stretches.empty:
                    st.error(f"Could not find any valid segments in {gear1_file.name}")
                if gear2_stretches.empty:
                    st.error(f"Could not find any valid segments in {gear2_file.name}")
    
    elif gear1_file:
        st.info("Please upload a GPX file for Gear 2 to compare")
    elif gear2_file:
        st.info("Please upload a GPX file for Gear 1 to compare")
    else:
        st.info("Upload GPX files for both gear types to see comparison")
        
        # Show example information
        st.markdown("### About Gear Comparison")
        st.markdown("""
        The gear comparison tool allows you to:
        
        1. Upload GPX files from two different sessions with different gear
        2. Automatically detect wind direction from each file (recommended)
        3. View side-by-side polar plots showing the performance of each setup
        4. See detailed metrics and head-to-head comparisons
        
        **Tips for best results:**
        * Use tracks from similar locations/conditions
        * Ensure both tracks have sufficient data (upwind and downwind sailing)
        * Let the system auto-detect wind direction for each track separately
        """)


# Run the app
if __name__ == "__main__":
    st_main()