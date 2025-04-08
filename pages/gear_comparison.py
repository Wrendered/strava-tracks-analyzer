import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
import os
import json
from datetime import datetime

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

from utils.visualization import plot_polar_diagram


def create_combined_polars(gear_data_list):
    """Create port/starboard polar half-circles with multiple gear plotted for comparison.
    
    Args:
        gear_data_list: List of dictionaries with keys 'stretches', 'name', 'wind_direction'
    """
    fig, (ax_port, ax_starboard) = plt.subplots(1, 2, figsize=(14, 7), subplot_kw={'projection': 'polar'})
    
    # Create title showing all compared gear
    gear_names = [gear['name'] for gear in gear_data_list]
    if len(gear_names) == 2:
        title = f"Gear Comparison: {gear_names[0]} vs {gear_names[1]}"
    else:
        title = f"Gear Comparison: {', '.join(gear_names[:-1])} and {gear_names[-1]}"
    plt.suptitle(title, fontsize=16)
    
    # Define colors for different gear - create a color cycle for many items
    colors = plt.cm.tab10.colors  # Use the tab10 colormap for up to 10 different gear
    
    # Get maximum speeds to make scales consistent
    max_speeds = []
    
    # Calculate max speeds from all gear
    for gear in gear_data_list:
        stretches = gear.get('stretches')
        if stretches is not None and not stretches.empty:
            max_speeds.append(stretches['speed'].max())
    
    # Set a default max_r if no data
    max_r = max(max_speeds) if max_speeds else 20
    
    # Plot port and starboard tack data
    plot_multi_polar(ax_port, ax_starboard, gear_data_list, colors, max_r)
    
    # Add legend for the gear types
    from matplotlib.lines import Line2D
    legend_elements = []
    
    for i, gear in enumerate(gear_data_list):
        color = colors[i % len(colors)]
        legend_elements.append(
            Line2D([0], [0], marker='o', color='w', markerfacecolor=color, 
                  markersize=8, label=gear['name'])
        )
    
    # Position the legend at the top to avoid overlapping with the text
    fig.legend(handles=legend_elements, loc='upper center', 
               bbox_to_anchor=(0.5, 0.96), ncol=min(len(gear_data_list), 4))
    
    # Adjust layout - make the plots closer together by adjusting wspace
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.09, top=0.90, wspace=-0.45)  # Negative wspace brings them closer
    
    return fig


def plot_multi_polar(ax_port, ax_starboard, gear_data_list, colors, max_r):
    """Plot both port and starboard polars with multiple gear datasets."""
    # Set up the port plot (LEFT PLOT)
    ax_port.set_theta_zero_location('N')  # 0 degrees at the top
    ax_port.set_theta_direction(1)  # counter-clockwise (mirrored)
    ax_port.set_thetamin(0)
    ax_port.set_thetamax(180)
    
    # Set up the starboard plot (RIGHT PLOT)
    ax_starboard.set_theta_zero_location('N')  # 0 degrees at the top
    ax_starboard.set_theta_direction(-1)  # clockwise
    ax_starboard.set_thetamin(0)
    ax_starboard.set_thetamax(180)
    
    # Set consistent speed rings for both plots
    radii = np.linspace(0, np.ceil(max_r), 6)
    ax_port.set_rticks(radii)
    ax_port.set_rlim(0, np.ceil(max_r) * 1.1)
    ax_starboard.set_rticks(radii)
    ax_starboard.set_rlim(0, np.ceil(max_r) * 1.1)
    
    # Plot data for each gear
    for i, gear in enumerate(gear_data_list):
        stretches = gear.get('stretches')
        if stretches is None or stretches.empty:
            continue
        
        # Convert from dict to DataFrame if needed (due to JSON serialization)
        if isinstance(stretches, dict):
            stretches = pd.DataFrame(stretches)
            
        color = colors[i % len(colors)]
        
        # PORT TACK
        port_data = stretches[stretches['tack'] == 'Port']
        if not port_data.empty:
            plot_tack_data(ax_port, port_data, color, marker='o', alpha=0.7)
        
        # STARBOARD TACK
        starboard_data = stretches[stretches['tack'] == 'Starboard']
        if not starboard_data.empty:
            plot_tack_data(ax_starboard, starboard_data, color, marker='s', alpha=0.7)
    
    # Add important angle reference lines to both plots
    angles = [0, 45, 90, 135, 180]
    labels = ["0°", "45°", "90°", "135°", "180°"]
    linestyles = [':', '--', '-', '--', ':']
    line_colors = ['black', 'red', 'green', 'orange', 'black']
    
    for angle, label, ls, color in zip(angles, labels, linestyles, line_colors):
        # Port plot
        ax_port.plot([np.radians(angle), np.radians(angle)], [0, max_r * 1.1], 
                ls=ls, color=color, alpha=0.5, linewidth=1)
        ax_port.text(np.radians(angle), max_r * 1.07, label, 
                ha='center', va='center', color=color, fontsize=9)
        
        # Starboard plot
        ax_starboard.plot([np.radians(angle), np.radians(angle)], [0, max_r * 1.1], 
                ls=ls, color=color, alpha=0.5, linewidth=1)
        ax_starboard.text(np.radians(angle), max_r * 1.07, label, 
                ha='center', va='center', color=color, fontsize=9)
    
    # Add titles
    ax_port.set_title('Port Tack', fontweight='bold', pad=15)
    ax_starboard.set_title('Starboard Tack', fontweight='bold', pad=15)




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


def create_gear_metrics_table(stretches, gear_info=None):
    """Create a metrics table for a single gear type."""
    if stretches.empty:
        st.info("No data available")
        return
    
    # Split by upwind/downwind
    upwind = stretches[stretches['angle_to_wind'] < 90]
    downwind = stretches[stretches['angle_to_wind'] >= 90]
    
    # Calculate metrics
    metrics = {}
    
    # Add gear info if available
    if gear_info:
        if gear_info.get('board'):
            metrics["Board"] = gear_info['board']
        if gear_info.get('foil'):
            metrics["Foil"] = gear_info['foil']
        if gear_info.get('wing'):
            metrics["Wing"] = gear_info['wing']
        if gear_info.get('wind_speed') and gear_info['wind_speed'] > 0:
            metrics["Wind Speed"] = f"{gear_info['wind_speed']} knots"
        if gear_info.get('wind_range'):
            metrics["Wind Range"] = gear_info['wind_range']
        if gear_info.get('conditions'):
            metrics["Conditions"] = gear_info['conditions']
    
    # Overall
    metrics["Overall Max Speed"] = f"{stretches['speed'].max():.1f} knots"
    metrics["Overall Avg Speed"] = f"{stretches['speed'].mean():.1f} knots"
    
    # Add Pointing Power metric with info icon
    pointing_power, port_best, starboard_best = calculate_pointing_power(stretches)
    if pointing_power is not None:
        if port_best is not None and starboard_best is not None:
            metrics["Pointing Power ℹ️"] = f"{pointing_power:.1f}° (P: {port_best:.1f}°, S: {starboard_best:.1f}°)"
        elif port_best is not None:
            metrics["Pointing Power ℹ️"] = f"{pointing_power:.1f}° (Port tack only)"
        elif starboard_best is not None:
            metrics["Pointing Power ℹ️"] = f"{pointing_power:.1f}° (Starboard tack only)"
    
    # Calculate clustered upwind speeds
    clustered_avg_speed, clustered_max_speed, cluster_indices, cluster_info = calculate_clustered_upwind_speed(stretches)
    
    # Add explanations
    if pointing_power is not None or (clustered_avg_speed is not None and clustered_max_speed is not None):
        with st.expander("About advanced metrics"):
            if pointing_power is not None:
                st.markdown("""
                **Pointing Power** is the average of the best pointing angles achieved on both port and starboard tack.
                
                It represents a gear setup's ability to sail close to the wind across both tacks, which is a key
                performance metric for upwind sailing. Lower numbers are better (closer to the wind).
                
                Formula: (Best Port Tack Angle + Best Starboard Tack Angle) / 2
                """)
                
            if clustered_avg_speed is not None:
                st.markdown("""
                **Clustered Upwind Speed** is based on a cluster of best pointing tacks, rather than all upwind tacks.
                
                The calculation:
                1. Identifies the best pointing tacks for each side (up to 3 per tack)
                2. Calculates the average pointing angle from these best tacks
                3. Includes only tacks that are within 10° of that average
                4. Calculates speed metrics from this cluster
                
                This approach gives a more accurate representation of upwind performance at competitive pointing angles.
                """)
                
                # Add cluster visualization
                if cluster_indices:
                    st.markdown("#### Visualization of Upwind Clusters")
                    st.markdown("Points in the upwind performance cluster are highlighted in solid colors:")
                    fig = visualize_upwind_clusters(stretches, cluster_indices)
                    if fig:
                        st.pyplot(fig)
    
    # Upwind
    if not upwind.empty:
        best_upwind_speed_idx = upwind['speed'].idxmax()
        max_upwind_speed = upwind.loc[best_upwind_speed_idx, 'speed']
        angle_at_max_speed = upwind.loc[best_upwind_speed_idx, 'angle_to_wind']
        
        min_upwind_angle = upwind['angle_to_wind'].min()
        min_angle_idx = upwind['angle_to_wind'].idxmin()
        speed_at_min_angle = upwind.loc[min_angle_idx, 'speed']
        
        # Add clustered upwind speed metrics
        if clustered_avg_speed is not None and clustered_max_speed is not None:
            metrics["Upwind - Clustered Avg Speed"] = f"{clustered_avg_speed:.1f} knots"
            metrics["Upwind - Clustered Max Speed"] = f"{clustered_max_speed:.1f} knots"
        
        # Traditional metrics
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
    sections = []
    
    # Gear info section if available
    if any(k in metrics for k in ["Board", "Foil", "Wing", "Wind Speed", "Wind Range", "Conditions"]):
        gear_keys = ["Board", "Foil", "Wing", "Wind Speed", "Wind Range", "Conditions"]
        gear_metrics = {k: v for k, v in metrics.items() if k in gear_keys}
        if gear_metrics:
            sections.append(("GEAR INFO", gear_metrics))
    
    # Performance metrics
    perf_keys = ["Overall Max Speed", "Overall Avg Speed", "Pointing Power ℹ️"]
    perf_metrics = {k: v for k, v in metrics.items() if k in perf_keys}
    if perf_metrics:
        sections.append(("OVERALL", perf_metrics))
    
    # Upwind metrics
    upwind_keys = ["Upwind - Best Pointing", "Upwind - Fastest", "Upwind - Avg Speed"]
    upwind_metrics = {k: v for k, v in metrics.items() if k in upwind_keys}
    if upwind_metrics:
        sections.append(("UPWIND", upwind_metrics))
    
    # Downwind metrics
    downwind_keys = ["Downwind - Deepest Run", "Downwind - Fastest", "Downwind - Avg Speed"]
    downwind_metrics = {k: v for k, v in metrics.items() if k in downwind_keys}
    if downwind_metrics:
        sections.append(("DOWNWIND", downwind_metrics))
    
    # Display with section headers
    for section_name, section_metrics in sections:
        st.markdown(f"**{section_name}**")
        section_df = pd.DataFrame(list(section_metrics.items()), columns=["Metric", "Value"])
        
        # Show explanation for Pointing Power
        if "Pointing Power ℹ️" in section_metrics:
            st.caption("ℹ️ Pointing Power is the average of the best pointing angles on port and starboard tacks. Lower numbers are better (closer to wind).")
            
        # Display table
        st.table(section_df)


def calculate_pointing_power(stretches):
    """Calculate pointing power - the average of best port and starboard tack pointing angles."""
    # Split by tack
    port_tack = stretches[(stretches['tack'] == 'Port') & (stretches['angle_to_wind'] < 90)]
    starboard_tack = stretches[(stretches['tack'] == 'Starboard') & (stretches['angle_to_wind'] < 90)]
    
    # Get best pointing angles
    if not port_tack.empty and not starboard_tack.empty:
        port_best = port_tack['angle_to_wind'].min()
        starboard_best = starboard_tack['angle_to_wind'].min()
        # Average the two best
        pointing_power = (port_best + starboard_best) / 2
        return pointing_power, port_best, starboard_best
    elif not port_tack.empty:
        # Only port tack data available
        port_best = port_tack['angle_to_wind'].min()
        return port_best, port_best, None
    elif not starboard_tack.empty:
        # Only starboard tack data available
        starboard_best = starboard_tack['angle_to_wind'].min()
        return starboard_best, None, starboard_best
    else:
        # No upwind data
        return None, None, None


def calculate_clustered_upwind_speed(stretches):
    """Calculate upwind speed metrics using clustering of best pointing angles.
    
    This uses the approach of finding the cluster of best pointing tacks and 
    calculating speed metrics based on only those tacks, rather than all upwind tacks.
    
    Returns:
        tuple: (avg_speed, max_speed, cluster_indices, cluster_info)
            - avg_speed: average speed of the clustered segments
            - max_speed: maximum speed of the clustered segments
            - cluster_indices: indices of segments in the cluster (for visualization)
            - cluster_info: dict with port and starboard tack cluster info
    """
    # Get upwind stretches
    upwind = stretches[stretches['angle_to_wind'] < 90]
    if upwind.empty:
        return None, None, None, None
    
    # Split by tack
    port_tack = upwind[upwind['tack'] == 'Port']
    starboard_tack = upwind[upwind['tack'] == 'Starboard']
    
    # Functions to process each tack
    def process_tack(tack_data):
        if tack_data.empty:
            return pd.DataFrame(), 0, []
        
        # Sort by angle to wind (ascending, best pointing first)
        sorted_tack = tack_data.sort_values('angle_to_wind')
        
        # Get up to 3 best pointing segments
        best_pointing = sorted_tack.head(min(3, len(sorted_tack)))
        
        # Calculate average of best pointing angles
        avg_angle = best_pointing['angle_to_wind'].mean()
        
        # Get all segments within 10 degrees of that average
        cluster_segments = tack_data[tack_data['angle_to_wind'] <= avg_angle + 10]
        
        # Get indices for visualization
        cluster_indices = cluster_segments.index.tolist()
        
        return cluster_segments, avg_angle, cluster_indices
    
    # Process each tack
    port_cluster, port_avg_angle, port_indices = process_tack(port_tack)
    starboard_cluster, starboard_avg_angle, starboard_indices = process_tack(starboard_tack)
    
    # Combine clusters
    combined_cluster = pd.concat([port_cluster, starboard_cluster])
    all_indices = port_indices + starboard_indices
    
    if combined_cluster.empty:
        return None, None, None, None
    
    # Calculate metrics
    avg_speed = combined_cluster['speed'].mean()
    max_speed = combined_cluster['speed'].max()
    
    # Create cluster info dict
    cluster_info = {
        'port': {
            'avg_angle': port_avg_angle if not port_cluster.empty else None,
            'count': len(port_cluster),
            'avg_speed': port_cluster['speed'].mean() if not port_cluster.empty else None
        },
        'starboard': {
            'avg_angle': starboard_avg_angle if not starboard_cluster.empty else None,
            'count': len(starboard_cluster),
            'avg_speed': starboard_cluster['speed'].mean() if not starboard_cluster.empty else None
        }
    }
    
    return avg_speed, max_speed, all_indices, cluster_info


def visualize_upwind_clusters(stretches, cluster_indices=None):
    """Create a scatter plot showing upwind performance with clusters highlighted."""
    if stretches.empty:
        return None
        
    # Filter for upwind data
    upwind = stretches[stretches['angle_to_wind'] < 90]
    if upwind.empty:
        return None
        
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot all upwind points
    port = upwind[upwind['tack'] == 'Port']
    starboard = upwind[upwind['tack'] == 'Starboard']
    
    ax.scatter(port['angle_to_wind'], port['speed'], 
              color='lightcoral', alpha=0.5, label='Port Tack')
    ax.scatter(starboard['angle_to_wind'], starboard['speed'], 
              color='lightblue', alpha=0.5, label='Starboard Tack')
    
    # Highlight clustered points if provided
    if cluster_indices:
        cluster = stretches.loc[cluster_indices]
        port_cluster = cluster[cluster['tack'] == 'Port']
        starboard_cluster = cluster[cluster['tack'] == 'Starboard']
        
        ax.scatter(port_cluster['angle_to_wind'], port_cluster['speed'], 
                  color='red', alpha=1.0, s=100, label='Port Cluster')
        ax.scatter(starboard_cluster['angle_to_wind'], starboard_cluster['speed'], 
                  color='blue', alpha=1.0, s=100, label='Starboard Cluster')
    
    # Add labels and styling
    ax.set_xlabel('Angle to Wind (degrees)')
    ax.set_ylabel('Speed (knots)')
    ax.set_title('Upwind Performance with High-Pointing Clusters')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Adjust axes
    ax.set_xlim(0, 90)
    
    return fig


def create_comparison_table(stretches1, stretches2, gear1_name, gear2_name, gear1_info=None, gear2_info=None):
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
        
        # Calculate pointing power for each gear
        pointing_power1, port_best1, starboard_best1 = calculate_pointing_power(stretches1)
        pointing_power2, port_best2, starboard_best2 = calculate_pointing_power(stretches2)
        
        if pointing_power1 is not None and pointing_power2 is not None:
            pointing_diff = pointing_power1 - pointing_power2
            upwind_comparison["Pointing Power"] = [
                f"{pointing_power1:.1f}°", 
                f"{pointing_power2:.1f}°",
                f"{abs(pointing_diff):.1f}° {gear2_name if pointing_diff > 0 else gear1_name}"
            ]
            
            # Replace expander with help tooltip
            upwind_comparison["Pointing Power ℹ️"] = [
                f"{pointing_power1:.1f}°", 
                f"{pointing_power2:.1f}°",
                f"{abs(pointing_diff):.1f}° {gear2_name if pointing_diff > 0 else gear1_name}"
            ]
            
            # Remove the previous entry without the help icon
            upwind_comparison.pop("Pointing Power")
        
        # Best pointing angle
        min_angle1 = upwind1['angle_to_wind'].min()
        min_angle2 = upwind2['angle_to_wind'].min()
        angle_diff = min_angle1 - min_angle2
        upwind_comparison["Best Pointing Angle"] = [
            f"{min_angle1:.1f}°", 
            f"{min_angle2:.1f}°",
            f"{abs(angle_diff):.1f}° {gear2_name if angle_diff > 0 else gear1_name}"
        ]
        
        # Calculate clustered upwind speeds
        clustered_avg_speed1, clustered_max_speed1, cluster_indices1, cluster_info1 = calculate_clustered_upwind_speed(stretches1)
        clustered_avg_speed2, clustered_max_speed2, cluster_indices2, cluster_info2 = calculate_clustered_upwind_speed(stretches2)
        
        # Explaining the clustered speed calculation
        with st.expander("About Upwind Speed Calculation"):
            st.markdown("""
            **Upwind Speed Calculation** is based on a cluster of best pointing tacks, rather than all upwind tacks.
            
            The calculation:
            1. Identifies the best pointing tacks for each side (up to 3 per tack)
            2. Calculates the average pointing angle from these best tacks
            3. Includes only tacks that are within 10° of that average
            4. Calculates speed metrics from this cluster
            
            This approach gives a more accurate representation of upwind performance at competitive pointing angles.
            """)
            
            # Add cluster visualizations
            if cluster_indices1 or cluster_indices2:
                cols = st.columns(2)
                
                with cols[0]:
                    if cluster_indices1:
                        st.markdown(f"**{gear1_name} Upwind Cluster**")
                        fig1 = visualize_upwind_clusters(stretches1, cluster_indices1)
                        if fig1:
                            st.pyplot(fig1)
                
                with cols[1]:
                    if cluster_indices2:
                        st.markdown(f"**{gear2_name} Upwind Cluster**")
                        fig2 = visualize_upwind_clusters(stretches2, cluster_indices2)
                        if fig2:
                            st.pyplot(fig2)
        
        # Average upwind speed (clustered approach)
        if clustered_avg_speed1 is not None and clustered_avg_speed2 is not None:
            upwind_avg_diff = clustered_avg_speed1 - clustered_avg_speed2
            upwind_comparison["Clustered Upwind Avg Speed"] = [
                f"{clustered_avg_speed1:.1f} knots", 
                f"{clustered_avg_speed2:.1f} knots",
                f"{abs(upwind_avg_diff):.1f} knots {gear1_name if upwind_avg_diff > 0 else gear2_name}"
            ]
        
        # Maximum upwind speed (clustered approach)
        if clustered_max_speed1 is not None and clustered_max_speed2 is not None:
            upwind_max_diff = clustered_max_speed1 - clustered_max_speed2
            upwind_comparison["Clustered Upwind Max Speed"] = [
                f"{clustered_max_speed1:.1f} knots", 
                f"{clustered_max_speed2:.1f} knots",
                f"{abs(upwind_max_diff):.1f} knots {gear1_name if upwind_max_diff > 0 else gear2_name}"
            ]
        
        # Traditional metrics as fallback
        # Average upwind speed (all upwind tacks)
        avg_upwind_speed1 = upwind1['speed'].mean()
        avg_upwind_speed2 = upwind2['speed'].mean()
        upwind_avg_diff = avg_upwind_speed1 - avg_upwind_speed2
        upwind_comparison["All Upwind Avg Speed"] = [
            f"{avg_upwind_speed1:.1f} knots", 
            f"{avg_upwind_speed2:.1f} knots",
            f"{abs(upwind_avg_diff):.1f} knots {gear1_name if upwind_avg_diff > 0 else gear2_name}"
        ]
        
        # Maximum upwind speed (all upwind tacks)
        max_upwind_speed1 = upwind1['speed'].max()
        max_upwind_speed2 = upwind2['speed'].max()
        upwind_max_diff = max_upwind_speed1 - max_upwind_speed2
        upwind_comparison["All Upwind Max Speed"] = [
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
        
        # Add caption for Pointing Power explanation
        if "Pointing Power ℹ️" in upwind_comparison:
            st.caption("ℹ️ Pointing Power is the average of the best pointing angles on port and starboard tacks. Lower numbers are better (closer to wind).")
            
        # Display table
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


def generate_session_card(session_data):
    """Generate a card-style display for a session."""
    with st.container(border=True):
        # Header with session name and date
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {session_data['name']}")
            if session_data.get('date'):
                try:
                    date_obj = datetime.fromisoformat(session_data['date'])
                    st.caption(f"📅 {date_obj.strftime('%B %d, %Y')}")
                except:
                    st.caption(f"📅 {session_data['date']}")
                    
        with col2:
            if session_data.get('location'):
                st.markdown(f"📍 **Location:** {session_data['location']}")
            
            # Wind info
            wind_info = []
            if session_data.get('wind_direction') is not None:
                wind_info.append(f"{session_data['wind_direction']:.0f}°")
            if session_data.get('wind_speed') and session_data['wind_speed'] > 0:
                wind_info.append(f"{session_data['wind_speed']} knots")
            if wind_info:
                st.markdown(f"💨 **Wind:** {' at '.join(wind_info)}")
        
        with col3:
            cols = st.columns(2)
            with cols[0]:
                st.button("View", key=f"view_{session_data['id']}", 
                          on_click=lambda: st.session_state.update({'selected_session': session_data['id']}))
            with cols[1]:
                st.button("Edit", key=f"edit_{session_data['id']}", 
                          on_click=lambda: st.session_state.update({'edit_session': session_data['id']}))
        
        # Gear info
        cols = st.columns(3)
        with cols[0]:
            if session_data.get('board'):
                st.markdown(f"**Board:** {session_data['board']}")
        with cols[1]:
            if session_data.get('foil'):
                st.markdown(f"**Foil:** {session_data['foil']}")
        with cols[2]:
            if session_data.get('wing'):
                st.markdown(f"**Wing:** {session_data['wing']}")
        
        # Show notes if available
        if session_data.get('notes'):
            with st.expander("Notes"):
                st.markdown(session_data['notes'])


def process_bulk_upload(uploaded_files):
    """Process multiple GPX files at once with minimal configuration."""
    from utils.gpx_parser import load_gpx_file
    from utils.calculations import calculate_track_metrics
    from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles, estimate_wind_direction
    import time
    
    # Progress bar
    progress_bar = st.progress(0, "Processing files...")
    file_count = len(uploaded_files)
    
    # Process each file
    for i, uploaded_file in enumerate(uploaded_files):
        progress_text = st.empty()
        progress_text.markdown(f"Processing file {i+1}/{file_count}: {uploaded_file.name}")
        progress_bar.progress((i / file_count) * 0.9)  # Use 90% of the progress bar for processing
        
        try:
            # Load GPX data
            gpx_result = load_gpx_file(uploaded_file)
            
            # Handle both old and new return formats
            if isinstance(gpx_result, tuple):
                gpx_data, metadata = gpx_result
                track_name = metadata.get('name', 'Unknown Track')
            else:
                gpx_data = gpx_result
                track_name = os.path.splitext(os.path.basename(uploaded_file.name))[0]
            
            if gpx_data.empty:
                continue
                
            # Default parameters (similar to main page)
            angle_tolerance = 12
            min_duration = 10
            min_distance = 50
            min_speed = 10.0  # knots
            min_speed_ms = min_speed * 0.514444  # Convert knots to m/s
            active_speed_threshold = 5.0  # knots
            
            # Calculate metrics
            metrics = calculate_track_metrics(gpx_data, min_speed_knots=active_speed_threshold)
            
            # Find segments
            stretches = find_consistent_angle_stretches(
                gpx_data, angle_tolerance, min_duration, min_distance
            )
            
            if stretches.empty:
                continue
                
            # Filter by minimum speed
            stretches = stretches[stretches['speed'] >= min_speed_ms]
            
            if stretches.empty:
                continue
                
            # Estimate wind direction
            try:
                # Try simple method first
                estimated_wind = estimate_wind_direction(stretches, use_simple_method=True)
                
                # If that fails, try complex method
                if estimated_wind is None:
                    estimated_wind = estimate_wind_direction(stretches, use_simple_method=False)
                
                # Use default if both fail
                if estimated_wind is None:
                    estimated_wind = 90
            except:
                estimated_wind = 90
            
            # Calculate angles relative to wind
            stretches = analyze_wind_angles(stretches, estimated_wind)
            
            # Create session data
            session_data = {
                'id': len(st.session_state.gear_comparison_data) + 1,
                'name': track_name,
                'date': None,
                'wind_direction': estimated_wind,
                'wind_speed': 0,
                'wind_range': '',
                'board': '',
                'foil': '',
                'wing': '',
                'location': '',
                'conditions': '',
                'notes': f"Auto-imported from {uploaded_file.name}",
                'metrics': metrics,
                'stretches': stretches
            }
            
            # Add to gear comparison data
            st.session_state.gear_comparison_data.append(session_data)
            
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            continue
    
    # Complete progress
    progress_bar.progress(1.0)
    time.sleep(0.5)
    progress_bar.empty()
    
    st.success(f"✅ Successfully processed {len(uploaded_files)} files")
    st.rerun()


def show_session_list(session_data_list):
    """Display a list of saved sessions."""
    st.subheader("Saved Gear Sessions")
    
    # Add bulk upload option
    with st.expander("⚡ Bulk Upload GPX Files"):
        st.markdown("""
        Upload multiple GPX files at once to quickly add sessions for comparison.
        
        **How it works:**
        1. Files will be processed with default settings
        2. Wind direction will be auto-estimated
        3. Sessions can be edited later to add details like gear info
        """)
        
        uploaded_files = st.file_uploader(
            "Select multiple GPX files", 
            type=['gpx'], 
            accept_multiple_files=True,
            key="bulk_gpx_uploader"
        )
        
        if uploaded_files:
            if st.button("Process Files", key="bulk_process", type="primary"):
                process_bulk_upload(uploaded_files)
    
    # Session management actions
    if len(session_data_list) > 0:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🗑️ Clear All", key="clear_all_sessions"):
                st.session_state.confirm_clear_all = True
                st.rerun()
        
        # Confirm deletion of all sessions
        if getattr(st.session_state, 'confirm_clear_all', False):
            st.warning("⚠️ Are you sure you want to delete ALL sessions?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Cancel", key="cancel_clear_all"):
                    st.session_state.confirm_clear_all = False
                    st.rerun()
            with col2:
                if st.button("Yes, delete all", key="confirm_clear_all", type="primary"):
                    st.session_state.gear_comparison_data = []
                    if 'selected_comparison_sessions' in st.session_state:
                        st.session_state.selected_comparison_sessions = []
                    st.session_state.confirm_clear_all = False
                    st.success("All sessions deleted")
                    st.rerun()
    
    if not session_data_list:
        st.info("No gear sessions saved. Use bulk upload above or go to the Track Analysis page to analyze and export sessions.")
        return
    
    # Sort by date if available, otherwise by ID
    sorted_sessions = sorted(
        session_data_list, 
        key=lambda x: (x.get('date', '0') or '0', x['id']), 
        reverse=True
    )
    
    # Display each session as a card
    for session in sorted_sessions:
        generate_session_card(session)
        st.markdown("---")


def edit_session(session_data):
    """Show form to edit session details."""
    # Header with back button
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("← Back"):
            st.session_state.edit_session = None
            st.rerun()
    with col2:
        st.header(f"Edit Session: {session_data['name']}")
    
    # Edit form
    with st.form("edit_session_form"):
        # Session name
        session_name = st.text_input("Session Name", value=session_data.get('name', ''))
        
        # Date picker
        try:
            current_date = datetime.fromisoformat(session_data.get('date', '')) if session_data.get('date') else None
        except:
            current_date = None
            
        session_date = st.date_input("Session Date", value=current_date)
        
        # Gear info
        col1, col2 = st.columns(2)
        with col1:
            board = st.text_input("Board", value=session_data.get('board', ''), placeholder="E.g., Axis S-Series 5'2\"")
            foil = st.text_input("Foil", value=session_data.get('foil', ''), placeholder="E.g., Armstrong CF2400")
        
        with col2:
            wing = st.text_input("Wing", value=session_data.get('wing', ''), placeholder="E.g., Duotone Unit 5m")
            wind_speed = st.number_input(
                "Avg Wind Speed (knots)", 
                min_value=0, max_value=50, 
                value=session_data.get('wind_speed', 0) if session_data.get('wind_speed') else 0, 
                step=1
            )
        
        # Wind and location info
        col1, col2 = st.columns(2)
        with col1:
            wind_range = st.text_input(
                "Wind Range", 
                value=session_data.get('wind_range', ''), 
                placeholder="E.g., 15-20 knots"
            )
            conditions = st.text_input(
                "Conditions", 
                value=session_data.get('conditions', ''), 
                placeholder="E.g., Choppy water, gusty"
            )
        
        with col2:
            location = st.text_input(
                "Location", 
                value=session_data.get('location', ''),
                placeholder="E.g., San Francisco Bay"
            )
            # We don't allow editing the wind direction - it's calculated from the data
        
        # Notes
        notes = st.text_area(
            "Notes", 
            value=session_data.get('notes', ''),
            placeholder="Any additional info about this session"
        )
        
        # Form submission
        col1, col2 = st.columns([1, 1])
        with col1:
            cancel = st.form_submit_button("Cancel", type="secondary")
        with col2:
            submit = st.form_submit_button("Save Changes", type="primary")
        
        if submit:
            # Update session data
            updated_session = session_data.copy()
            updated_session.update({
                'name': session_name,
                'date': session_date.isoformat() if session_date else None,
                'board': board,
                'foil': foil,
                'wing': wing,
                'wind_speed': wind_speed,
                'wind_range': wind_range,
                'conditions': conditions,
                'location': location,
                'notes': notes
            })
            
            # Find the session in the list and update it
            for i, s in enumerate(st.session_state.gear_comparison_data):
                if s['id'] == session_data['id']:
                    st.session_state.gear_comparison_data[i] = updated_session
                    break
            
            # Return to session list
            st.session_state.edit_session = None
            st.success("Session updated successfully!")
            st.rerun()
            
        if cancel:
            st.session_state.edit_session = None
            st.rerun()


def show_session_detail(session_data):
    """Show detailed view of a single session."""
    # Header with back button
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.selected_session = None
            st.rerun()
    with col2:
        st.header(session_data['name'])
    with col3:
        if st.button("Edit", key="edit_detail"):
            st.session_state.edit_session = session_data['id']
            st.session_state.selected_session = None
            st.rerun()
    
    # Overview info
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            if session_data.get('date'):
                try:
                    date_obj = datetime.fromisoformat(session_data['date'])
                    st.markdown(f"**📅 Date:** {date_obj.strftime('%B %d, %Y')}")
                except:
                    st.markdown(f"**📅 Date:** {session_data['date']}")
            
            if session_data.get('location'):
                st.markdown(f"**📍 Location:** {session_data['location']}")
            
            if session_data.get('conditions'):
                st.markdown(f"**🌊 Conditions:** {session_data['conditions']}")
        
        with col2:
            # Wind info
            wind_info = []
            if session_data.get('wind_direction') is not None:
                wind_info.append(f"{session_data['wind_direction']:.0f}°")
            if session_data.get('wind_speed') and session_data['wind_speed'] > 0:
                wind_info.append(f"{session_data['wind_speed']} knots")
            if session_data.get('wind_range'):
                wind_info.append(f"Range: {session_data['wind_range']}")
            if wind_info:
                st.markdown(f"**💨 Wind:** {' | '.join(wind_info)}")
            
            # Gear info
            gear_info = []
            if session_data.get('board'):
                gear_info.append(f"Board: {session_data['board']}")
            if session_data.get('foil'):
                gear_info.append(f"Foil: {session_data['foil']}")
            if session_data.get('wing'):
                gear_info.append(f"Wing: {session_data['wing']}")
            if gear_info:
                st.markdown(f"**🏄 Gear:** {' | '.join(gear_info)}")
    
    # Show notes if available
    if session_data.get('notes'):
        st.markdown("#### Notes")
        st.markdown(session_data['notes'])
    
    # Performance visualization
    st.markdown("### Performance Analysis")
    
    # Get stretches data
    stretches = session_data.get('stretches')
    if stretches is not None and not stretches.empty:
        if isinstance(stretches, dict):  # Handle JSON serialized DataFrame
            stretches = pd.DataFrame(stretches)
        
        # Show polar diagram
        fig = plot_polar_diagram(stretches, session_data['wind_direction'])
        st.pyplot(fig)
        
        # Create metrics table
        st.markdown("### Performance Metrics")
        
        # Format gear info for metrics table
        gear_info = {
            'board': session_data.get('board'),
            'foil': session_data.get('foil'),
            'wing': session_data.get('wing'),
            'wind_speed': session_data.get('wind_speed'),
            'wind_range': session_data.get('wind_range'),
            'conditions': session_data.get('conditions')
        }
        
        create_gear_metrics_table(stretches, gear_info)
        
        # Add compare button
        if st.button("Add to Comparison", key="add_to_comparison"):
            # Add to selected session IDs for comparison
            if 'selected_comparison_sessions' not in st.session_state:
                st.session_state.selected_comparison_sessions = []
                
            if session_data['id'] not in st.session_state.selected_comparison_sessions:
                st.session_state.selected_comparison_sessions.append(session_data['id'])
                st.success(f"Added '{session_data['name']}' to comparison. Go to Compare tab to view.")
            else:
                st.info(f"'{session_data['name']}' is already in the comparison.")
        
    else:
        st.warning("No segment data available for this session.")
    
    # Delete button
    if st.button("Delete Session", type="primary", key="delete_session"):
        st.session_state.confirm_delete = session_data['id']
    
    # Confirm delete
    if getattr(st.session_state, 'confirm_delete', None) == session_data['id']:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancel", key="cancel_delete"):
                st.session_state.confirm_delete = None
        with col2:
            if st.button("Confirm Delete", key="confirm_delete", type="primary"):
                # Remove from list
                st.session_state.gear_comparison_data = [
                    s for s in st.session_state.gear_comparison_data 
                    if s['id'] != session_data['id']
                ]
                # Remove from selected comparison sessions if present
                if 'selected_comparison_sessions' in st.session_state and session_data['id'] in st.session_state.selected_comparison_sessions:
                    st.session_state.selected_comparison_sessions.remove(session_data['id'])
                    
                # Reset view
                st.session_state.selected_session = None
                st.session_state.confirm_delete = None
                st.success("Session deleted!")
                st.rerun()


def select_sessions_sidebar(gear_data_list):
    """Show session selection checkboxes in the sidebar.
    
    Returns:
        list: List of selected session data
    """
    if len(gear_data_list) < 2:
        st.sidebar.warning("Need at least two saved sessions. Go to Track Analysis to save more sessions.")
        return []
    
    # Sort by date if available, otherwise by ID
    sorted_sessions = sorted(
        gear_data_list, 
        key=lambda x: (x.get('date', '0') or '0', x['id']), 
        reverse=True
    )
    
    # Initialize selected sessions in session state if not already there
    if 'selected_comparison_sessions' not in st.session_state:
        # Default to selecting the first two sessions
        st.session_state.selected_comparison_sessions = [sorted_sessions[0]['id'], sorted_sessions[1]['id']] if len(sorted_sessions) >= 2 else []
    
    st.sidebar.markdown("### Select Sessions to Compare")
    
    # Create a checkbox for each session
    selected_session_ids = []
    for i, session in enumerate(sorted_sessions):
        # Create a checkbox for each session
        is_selected = session['id'] in st.session_state.selected_comparison_sessions
        if st.sidebar.checkbox(
            f"{session['name']} ({session.get('date', 'No date')})",
            value=is_selected,
            key=f"select_{session['id']}"
        ):
            selected_session_ids.append(session['id'])
    
    # Update session state
    st.session_state.selected_comparison_sessions = selected_session_ids
    
    # Create apply button
    if st.sidebar.button("Apply Selection", type="primary", key="apply_session_selection"):
        st.rerun()
    
    # Return the selected sessions data
    selected_sessions = [s for s in sorted_sessions if s['id'] in selected_session_ids]
    return selected_sessions


def run_multi_comparison(selected_sessions):
    """Run detailed comparison between multiple gear sessions."""
    # Generate header with all session names
    if len(selected_sessions) == 2:
        header_text = f"Comparison: {selected_sessions[0]['name']} vs {selected_sessions[1]['name']}"
    else:
        names = [s['name'] for s in selected_sessions]
        header_text = f"Multi-Gear Comparison: {', '.join(names[:-1])} and {names[-1]}"
    
    st.header(header_text)
    
    # Process stretches data for all sessions
    for session in selected_sessions:
        stretches = session.get('stretches')
        
        # Convert from dict to DataFrame if needed (due to JSON serialization)
        if isinstance(stretches, dict):
            session['stretches'] = pd.DataFrame(stretches)
            
        # Ensure we have data
        if session['stretches'] is None or session['stretches'].empty:
            st.warning(f"Session '{session['name']}' has no segment data.")
            return
    
    # Plot the comparative polar diagram
    st.write("### Polar Performance Comparison")
    fig = create_combined_polars(selected_sessions)
    st.pyplot(fig)
    
    # Show gear specs comparison
    st.write("### Gear Specifications")
    
    # Create comparison table with all gear specs
    gear_comparison = {}
    for field in ['board', 'foil', 'wing', 'wind_speed', 'wind_range', 'conditions', 'location']:
        # Collect values from all sessions
        has_value = False
        field_values = []
        
        for session in selected_sessions:
            val = session.get(field, 'N/A')
            
            # Format wind_speed with "knots" if available
            if field == 'wind_speed' and val != 'N/A' and val > 0:
                val = f"{val} knots"
                
            field_values.append(val)
            if val != 'N/A':
                has_value = True
        
        # Skip if no session has a value for this field
        if not has_value:
            continue
            
        # Add to comparison dict
        gear_comparison[field.capitalize()] = field_values
    
    # Create comparison table if we have specs
    if gear_comparison:
        column_names = [s['name'] for s in selected_sessions]
        gear_df = pd.DataFrame.from_dict(
            gear_comparison,
            orient='index',
            columns=column_names
        )
        st.table(gear_df)
    
    # Create comparison tables for performance metrics
    st.write("### Performance Comparison")
    
    # Create a DataFrame with key metrics for all sessions
    metrics_data = []
    
    for session in selected_sessions:
        stretches = session['stretches']
        
        # Calculate key metrics
        upwind = stretches[stretches['angle_to_wind'] < 90]
        downwind = stretches[stretches['angle_to_wind'] >= 90]
        
        # Calculate pointing power
        pointing_power, _, _ = calculate_pointing_power(stretches)
        
        # Calculate clustered upwind speed
        clustered_avg_speed, clustered_max_speed, _, _ = calculate_clustered_upwind_speed(stretches)
        
        # Create metrics row
        row = {
            'Session': session['name'],
            'Pointing Power (°)': round(pointing_power, 1) if pointing_power is not None else 'N/A',
            'Best Upwind Angle (°)': round(upwind['angle_to_wind'].min(), 1) if not upwind.empty else 'N/A',
            'Clustered Upwind Speed (knots)': round(clustered_avg_speed, 1) if clustered_avg_speed is not None else 'N/A',
            'Max Speed (knots)': round(stretches['speed'].max(), 1),
            'Avg Speed (knots)': round(stretches['speed'].mean(), 1),
            'Best Downwind Angle (°)': round(downwind['angle_to_wind'].max(), 1) if not downwind.empty else 'N/A',
            'Downwind Avg Speed (knots)': round(downwind['speed'].mean(), 1) if not downwind.empty else 'N/A'
        }
        
        metrics_data.append(row)
    
    # Create DataFrame and display
    metrics_df = pd.DataFrame(metrics_data)
    
    # Show tooltip separately instead of in the dataframe parameters
    st.info("""
    **Pointing Power**: Average of best port/starboard pointing angles. Lower is better (closer to wind).
    **Clustered Upwind Speed**: Average speed calculated from the cluster of best pointing segments.
    """)
    
    # Display dataframe - check if hide_index is supported in your Streamlit version
    try:
        # For newer versions of Streamlit
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    except:
        # Fallback for older versions
        st.dataframe(metrics_df, use_container_width=True)
    
    # Explain the clustering calculation in an expander
    with st.expander("About Upwind Speed Calculation"):
        st.markdown("""
        **Clustered Upwind Speed** is based on a cluster of best pointing tacks, rather than all upwind tacks.
        
        The calculation:
        1. Identifies the best pointing tacks for each side (up to 3 per tack)
        2. Calculates the average pointing angle from these best tacks
        3. Includes only tacks that are within 10° of that average
        4. Calculates speed metrics from this cluster
        
        This approach gives a more accurate representation of upwind performance at competitive pointing angles.
        """)
    
    # Generate visualization for each session's upwind clusters
    with st.expander("Upwind Clusters Visualization"):
        # Split into rows with 2 sessions per row
        for i in range(0, len(selected_sessions), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(selected_sessions):
                    session = selected_sessions[i + j]
                    with cols[j]:
                        st.markdown(f"**{session['name']} Upwind Cluster**")
                        
                        # Calculate clusters
                        _, _, cluster_indices, _ = calculate_clustered_upwind_speed(session['stretches'])
                        
                        # Create visualization
                        if cluster_indices:
                            fig = visualize_upwind_clusters(session['stretches'], cluster_indices)
                            if fig:
                                st.pyplot(fig)
    
    # Add AI analysis section (placeholder for future implementation)
    st.write("### AI Performance Analysis")
    if st.button("Generate AI Analysis", key="generate_ai_analysis"):
        with st.spinner("Analyzing performance data..."):
            st.info("AI analysis feature coming soon! This will generate natural language insights about performance differences.")


def st_main():
    """Main gear comparison UI."""
    st.header("🔄 Gear Comparison")
    
    # Initialize key state variables if not already set
    if 'gear_comparison_data' not in st.session_state:
        st.session_state.gear_comparison_data = []
    
    if 'selected_session' not in st.session_state:
        st.session_state.selected_session = None
        
    if 'edit_session' not in st.session_state:
        st.session_state.edit_session = None
    
    # Selection sidebar (visible everywhere) - show on all pages to make it easy to compare
    selected_sessions = select_sessions_sidebar(st.session_state.gear_comparison_data)
    
    # Main page flow control based on state
    if st.session_state.edit_session is not None:
        # Edit view for a specific session
        session_to_edit = next(
            (s for s in st.session_state.gear_comparison_data if s['id'] == st.session_state.edit_session), 
            None
        )
        if session_to_edit:
            edit_session(session_to_edit)
        else:
            st.error("Session not found.")
            st.session_state.edit_session = None
            st.rerun()
    elif st.session_state.selected_session is not None:
        # Detail view for a specific session
        session = next(
            (s for s in st.session_state.gear_comparison_data if s['id'] == st.session_state.selected_session), 
            None
        )
        if session:
            show_session_detail(session)
        else:
            st.error("Session not found.")
            st.session_state.selected_session = None
            st.rerun()
    else:
        # Main gear comparison view
        st.write("Compare performance between different gear setups.")
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📋 Saved Sessions", "📊 Compare"])
        
        with tab1:
            # Show list of all saved sessions
            show_session_list(st.session_state.gear_comparison_data)
            
        with tab2:
            # Compare multiple sessions
            if len(selected_sessions) >= 2:
                # Run the comparison with all selected sessions
                run_multi_comparison(selected_sessions)
            else:
                st.info("Select at least two sessions from the sidebar to compare.")
                
                # If we have sessions but none selected, prompt the user
                if len(st.session_state.gear_comparison_data) >= 2:
                    st.markdown("### How to use the comparison tool:")
                    st.markdown("""
                    1. Select the sessions you want to compare from the sidebar on the left
                    2. Click "Apply Selection" to view the comparison
                    3. You can select and compare as many sessions as you want
                    
                    The comparison will show:
                    - A combined polar diagram with all selected sessions
                    - Gear specifications table
                    - Performance metrics comparison
                    - Visualization of upwind clusters for each session
                    """)
            
            if len(st.session_state.gear_comparison_data) < 2:
                st.warning("Add at least two sessions from the Track Analysis page to enable comparisons.")


# Run the app if called directly
if __name__ == "__main__":
    st_main()