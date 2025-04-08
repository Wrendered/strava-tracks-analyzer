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


def create_combined_polars(gear1_stretches, gear2_stretches, gear1_name, gear2_name, wind_direction1, wind_direction2):
    """Create port/starboard polar half-circles with both gear on each plot for direct comparison."""
    fig, (ax_port, ax_starboard) = plt.subplots(1, 2, figsize=(14, 7), subplot_kw={'projection': 'polar'})
    
    plt.suptitle(f"Gear Comparison: {gear1_name} vs {gear2_name}", fontsize=16)
    
    # Define colors for each gear
    gear1_color = 'red'
    gear2_color = 'blue'
    
    # Get maximum speeds to make scales consistent
    max_speeds = []
    
    # Calculate max speeds from both gears
    if not gear1_stretches.empty:
        max_speeds.append(gear1_stretches['speed'].max())
    if not gear2_stretches.empty:
        max_speeds.append(gear2_stretches['speed'].max())
    
    # Set a default max_r if no data
    max_r = max(max_speeds) if max_speeds else 20
    
    # Plot PORT tack data (LEFT PLOT)
    plot_port_polar(
        ax_port, gear1_stretches, gear2_stretches, 
        gear1_name, gear2_name, 
        gear1_color, gear2_color,
        wind_direction1, wind_direction2,
        max_r
    )
    
    # Plot STARBOARD tack data (RIGHT PLOT)
    plot_starboard_polar(
        ax_starboard, gear1_stretches, gear2_stretches, 
        gear1_name, gear2_name, 
        gear1_color, gear2_color,
        wind_direction1, wind_direction2,
        max_r
    )
    
    # Add legend for the gear types
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=gear1_color, markersize=8, label=gear1_name),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=gear2_color, markersize=8, label=gear2_name)
    ]
    # Position the legend at the top to avoid overlapping with the text
    fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.96), ncol=2)
    
    # Add explanatory text with better spacing
    plt.figtext(0.5, 0.01, 
               "These polar plots show speed (radius) at different angles to the wind.\n" +
               "0° is directly into the wind (top), 90° is across (sides), 180° is directly downwind (bottom).\n" +
               "Marker size indicates distance sailed at this angle/speed combination.",
               ha='center', fontsize=9, wrap=True)
    
    # Adjust layout - increase bottom margin to give text more room
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.17, top=0.90)
    
    return fig


def plot_port_polar(ax, gear1_stretches, gear2_stretches, gear1_name, gear2_name, gear1_color, gear2_color, wind_direction1, wind_direction2, max_r):
    """Plot port tack data for both gears on the same axis."""
    # Set up the polar plot
    ax.set_theta_zero_location('N')  # 0 degrees at the top
    ax.set_theta_direction(-1)  # clockwise
    
    # Set the theta limits to 0-180 degrees (only show the top half)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    
    # Set consistent speed rings
    radii = np.linspace(0, np.ceil(max_r), 6)
    ax.set_rticks(radii)
    ax.set_rlim(0, np.ceil(max_r) * 1.1)
    
    # Filter for Port tack data for both gears
    if not gear1_stretches.empty:
        port_data1 = gear1_stretches[gear1_stretches['tack'] == 'Port'].copy()
        plot_tack_data(ax, port_data1, gear1_color, marker='o', alpha=0.7)
    
    if not gear2_stretches.empty:
        port_data2 = gear2_stretches[gear2_stretches['tack'] == 'Port'].copy()
        plot_tack_data(ax, port_data2, gear2_color, marker='o', alpha=0.7)
    
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
    
    # Add title
    ax.set_title('Port Tack', fontweight='bold', pad=15)


def plot_starboard_polar(ax, gear1_stretches, gear2_stretches, gear1_name, gear2_name, gear1_color, gear2_color, wind_direction1, wind_direction2, max_r):
    """Plot starboard tack data for both gears on the same axis."""
    # Set up the polar plot
    ax.set_theta_zero_location('N')  # 0 degrees at the top
    ax.set_theta_direction(-1)  # clockwise
    
    # Set the theta limits to 0-180 degrees (only show the top half)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    
    # Set consistent speed rings
    radii = np.linspace(0, np.ceil(max_r), 6)
    ax.set_rticks(radii)
    ax.set_rlim(0, np.ceil(max_r) * 1.1)
    
    # Filter for Starboard tack data for both gears
    if not gear1_stretches.empty:
        starboard_data1 = gear1_stretches[gear1_stretches['tack'] == 'Starboard'].copy()
        plot_tack_data(ax, starboard_data1, gear1_color, marker='s', alpha=0.7)
    
    if not gear2_stretches.empty:
        starboard_data2 = gear2_stretches[gear2_stretches['tack'] == 'Starboard'].copy()
        plot_tack_data(ax, starboard_data2, gear2_color, marker='s', alpha=0.7)
    
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
    
    # Add title
    ax.set_title('Starboard Tack', fontweight='bold', pad=15)


def plot_tack_data(ax, tack_data, color, marker='o', alpha=0.7):
    """Plot data points for a specific tack and gear."""
    if tack_data.empty:
        return
    
    # Get values
    thetas = np.radians(tack_data['angle_to_wind'].values)
    r = tack_data['speed'].values  # Speed in knots
    weights = tack_data['distance'].values
    
    # Normalize weights for scatter size
    norm_weights = 20 * weights / weights.max() + 10 if weights.max() > 0 else 10
    
    # Plot the points
    ax.scatter(
        thetas, r, 
        color=color, s=norm_weights, alpha=alpha, 
        marker=marker, edgecolors='none'
    )


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
    fig = create_combined_polars(
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
        gpx_result = load_gpx_file(uploaded_file)
        
        # Handle both old and new return formats
        if isinstance(gpx_result, tuple):
            gpx_data, metadata = gpx_result
        else:
            gpx_data = gpx_result
            metadata = {'name': None}
        
        logger.info(f"Loaded GPX file with {len(gpx_data)} points")
        
        # Extract track name from metadata or filename
        if metadata.get('name'):
            track_name = metadata['name']
        elif hasattr(uploaded_file, 'name'):
            # Use the filename without extension
            filename = os.path.basename(uploaded_file.name)
            track_name = os.path.splitext(filename)[0]
        else:
            track_name = "Unknown Track"
            
    except Exception as e:
        logger.error(f"Error loading GPX file: {str(e)}")
        st.error(f"Error loading GPX file: {str(e)}")
        return pd.DataFrame(), None, None, None, "Unknown Track"
    
    if gpx_data.empty:
        return pd.DataFrame(), None, None, None, track_name
    
    # Calculate basic track metrics
    metrics = calculate_track_metrics(gpx_data, min_speed_knots=active_speed_threshold)
    
    # Find consistent angle stretches
    stretches = find_consistent_angle_stretches(
        gpx_data, angle_tolerance, min_duration, min_distance
    )
    
    if stretches.empty:
        return pd.DataFrame(), None, None, None, track_name
    
    # Filter by minimum speed
    stretches = stretches[stretches['speed'] >= min_speed_ms]
    
    if stretches.empty:
        return pd.DataFrame(), None, None, None, track_name
    
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
    
    return stretches, metrics, estimated_wind, wind_message, track_name


def st_main():
    st.header("Gear Comparison")
    st.markdown("Compare performance between different gear types")
    
    # Initialize session state for gear comparison
    if 'gear1_data' not in st.session_state:
        st.session_state.gear1_data = None
        
    if 'gear1_name' not in st.session_state:
        st.session_state.gear1_name = None
        
    if 'gear1_stretches' not in st.session_state:
        st.session_state.gear1_stretches = None
        
    if 'gear1_wind' not in st.session_state:
        st.session_state.gear1_wind = None
        
    if 'gear2_data' not in st.session_state:
        st.session_state.gear2_data = None
        
    if 'gear2_name' not in st.session_state:
        st.session_state.gear2_name = None
        
    if 'gear2_stretches' not in st.session_state:
        st.session_state.gear2_stretches = None
        
    if 'gear2_wind' not in st.session_state:
        st.session_state.gear2_wind = None
        
    if 'gear_wind_autodetect' not in st.session_state:
        st.session_state.gear_wind_autodetect = True
    
    # Common settings for both files
    with st.sidebar:
        st.header("Gear Comparison Parameters")
        
        # Add button to clear gear data
        if st.session_state.gear1_data is not None or st.session_state.gear2_data is not None:
            if st.button("Clear All Gear Data"):
                st.session_state.gear1_data = None
                st.session_state.gear1_name = None
                st.session_state.gear1_stretches = None
                st.session_state.gear1_wind = None
                st.session_state.gear2_data = None
                st.session_state.gear2_name = None
                st.session_state.gear2_stretches = None
                st.session_state.gear2_wind = None
                st.rerun()
        
        # Wind direction auto-detection
        st.subheader("Wind Direction")
        wind_autodetect = st.checkbox(
            "Auto-detect Wind Direction (recommended)", 
            value=st.session_state.gear_wind_autodetect,
            help="Automatically estimate wind direction from track data (recommended for comparison)"
        )
        
        # Update in session state
        st.session_state.gear_wind_autodetect = wind_autodetect
        
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
        gear1_file = st.file_uploader("Upload GPX for Gear 1", type=["gpx"], key="gear1_uploader")
        gear1_name_default = "Gear 1"
        gear1_name_input = st.text_input(
            "Gear 1 Name (Optional)", 
            value=st.session_state.gear1_name if st.session_state.gear1_name else "",
            placeholder="Auto-detected from GPX if available",
            key="gear1_name_input"
        )
        
        # Show clear button for individual gear
        if st.session_state.gear1_data is not None:
            if st.button("Clear Gear 1 Data", key="clear_gear1"):
                st.session_state.gear1_data = None
                st.session_state.gear1_name = None
                st.session_state.gear1_stretches = None
                st.session_state.gear1_wind = None
                st.rerun()
    
    with col2:
        st.subheader("Gear 2")
        gear2_file = st.file_uploader("Upload GPX for Gear 2", type=["gpx"], key="gear2_uploader")
        gear2_name_default = "Gear 2"
        gear2_name_input = st.text_input(
            "Gear 2 Name (Optional)", 
            value=st.session_state.gear2_name if st.session_state.gear2_name else "",
            placeholder="Auto-detected from GPX if available",
            key="gear2_name_input"
        )
        
        # Show clear button for individual gear
        if st.session_state.gear2_data is not None:
            if st.button("Clear Gear 2 Data", key="clear_gear2"):
                st.session_state.gear2_data = None
                st.session_state.gear2_name = None
                st.session_state.gear2_stretches = None
                st.session_state.gear2_wind = None
                st.rerun()
    
    # Process files and create comparison
    # Check if we have new files to process or use existing data from session state
    process_gear1 = gear1_file is not None
    process_gear2 = gear2_file is not None
    
    # Use session state data if available
    if not process_gear1 and st.session_state.gear1_stretches is not None:
        gear1_stretches = st.session_state.gear1_stretches
        gear1_wind = st.session_state.gear1_wind
        gear1_display_name = st.session_state.gear1_name
        gear1_wind_msg = f"Using saved wind direction: {gear1_wind:.1f}°"
        gear1_available = True
    else:
        gear1_available = process_gear1
        
    if not process_gear2 and st.session_state.gear2_stretches is not None:
        gear2_stretches = st.session_state.gear2_stretches
        gear2_wind = st.session_state.gear2_wind
        gear2_display_name = st.session_state.gear2_name
        gear2_wind_msg = f"Using saved wind direction: {gear2_wind:.1f}°"
        gear2_available = True
    else:
        gear2_available = process_gear2
    
    # Process new files if needed
    if process_gear1 or process_gear2:
        with st.spinner("Processing GPX files..."):
            if process_gear1:
                # Process gear 1 file
                gear1_result = process_gpx_file(
                    gear1_file, angle_tolerance, min_duration, 
                    min_distance, min_speed_ms, active_speed_threshold
                )
                
                # Unpack results
                if len(gear1_result) == 5:
                    gear1_stretches, gear1_metrics, gear1_wind, gear1_wind_msg, gear1_auto_name = gear1_result
                    # Use input name or auto-detected name
                    gear1_display_name = gear1_name_input if gear1_name_input.strip() else gear1_auto_name
                    # Store in session state
                    st.session_state.gear1_stretches = gear1_stretches
                    st.session_state.gear1_wind = gear1_wind
                    st.session_state.gear1_name = gear1_display_name
                    st.session_state.gear1_data = True
                else:
                    # Handle older return format for backward compatibility
                    gear1_stretches = gear1_result[0]
                    gear1_metrics = gear1_result[1] if len(gear1_result) > 1 else None
                    gear1_wind = gear1_result[2] if len(gear1_result) > 2 else 90
                    gear1_wind_msg = gear1_result[3] if len(gear1_result) > 3 else "No wind direction detected"
                    gear1_display_name = gear1_name_input if gear1_name_input.strip() else gear1_name_default
                    # Store in session state
                    st.session_state.gear1_stretches = gear1_stretches
                    st.session_state.gear1_wind = gear1_wind
                    st.session_state.gear1_name = gear1_display_name
                    st.session_state.gear1_data = True
            
            if process_gear2:
                # Process gear 2 file
                gear2_result = process_gpx_file(
                    gear2_file, angle_tolerance, min_duration,
                    min_distance, min_speed_ms, active_speed_threshold
                )
                
                # Unpack results
                if len(gear2_result) == 5:
                    gear2_stretches, gear2_metrics, gear2_wind, gear2_wind_msg, gear2_auto_name = gear2_result
                    # Use input name or auto-detected name
                    gear2_display_name = gear2_name_input if gear2_name_input.strip() else gear2_auto_name
                    # Store in session state
                    st.session_state.gear2_stretches = gear2_stretches
                    st.session_state.gear2_wind = gear2_wind
                    st.session_state.gear2_name = gear2_display_name
                    st.session_state.gear2_data = True
                else:
                    # Handle older return format for backward compatibility
                    gear2_stretches = gear2_result[0]
                    gear2_metrics = gear2_result[1] if len(gear2_result) > 1 else None
                    gear2_wind = gear2_result[2] if len(gear2_result) > 2 else 90
                    gear2_wind_msg = gear2_result[3] if len(gear2_result) > 3 else "No wind direction detected"
                    gear2_display_name = gear2_name_input if gear2_name_input.strip() else gear2_name_default
                    # Store in session state
                    st.session_state.gear2_stretches = gear2_stretches
                    st.session_state.gear2_wind = gear2_wind
                    st.session_state.gear2_name = gear2_display_name
                    st.session_state.gear2_data = True
            
    
    # If we have both gear data available (either from new files or session state)
    if (gear1_available and gear2_available) or (process_gear1 and process_gear2):
        # Display wind direction messages
        st.info(f"Gear 1 ({gear1_display_name}): {gear1_wind_msg}")
        st.info(f"Gear 2 ({gear2_display_name}): {gear2_wind_msg}")
        
        # If manual wind direction was specified
        if not wind_autodetect and 'wind_direction' in locals():
            gear1_wind = wind_direction
            gear2_wind = wind_direction
            st.warning(f"Using manual wind direction: {wind_direction}° for both tracks (not recommended)")
        
        # Display comparison if both files were processed successfully
        if not gear1_stretches.empty and not gear2_stretches.empty:
            create_polar_comparison_section(
                gear1_stretches, gear2_stretches, 
                gear1_display_name, gear2_display_name, 
                gear1_wind, gear2_wind
            )
        else:
            if gear1_stretches.empty and process_gear1:
                st.error(f"Could not find any valid segments in {gear1_file.name}")
            elif gear1_stretches.empty:
                st.error("No valid segments in Gear 1 data")
                
            if gear2_stretches.empty and process_gear2:
                st.error(f"Could not find any valid segments in {gear2_file.name}")
            elif gear2_stretches.empty:
                st.error("No valid segments in Gear 2 data")
    
    # Handle cases where we only have one gear or no gears
    elif gear1_available or process_gear1:
        st.info("Please upload or select a GPX file for Gear 2 to compare")
    elif gear2_available or process_gear2:
        st.info("Please upload or select a GPX file for Gear 1 to compare")
    else:
        st.info("Upload GPX files for both gear types to see comparison")
        
        # Show example information
        st.markdown("### About Gear Comparison")
        st.markdown("""
        The gear comparison tool allows you to:
        
        1. Upload GPX files from two different sessions with different gear
        2. Automatically detect wind direction from each file (recommended)
        3. Compare port and starboard performance side-by-side
        4. See detailed metrics and head-to-head comparisons
        
        **Tips for best results:**
        * Use tracks from similar locations/conditions
        * Ensure both tracks have sufficient data (upwind and downwind sailing)
        * Let the system auto-detect wind direction for each track separately
        * The gear name will be auto-detected from your GPX files when possible
        """)


# Run the app
if __name__ == "__main__":
    st_main()