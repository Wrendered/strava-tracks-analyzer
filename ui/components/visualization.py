"""
Data visualization components for the Foil Lab app.

This module contains functions for visualizing track data, segments,
and wind analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

logger = logging.getLogger(__name__)

def display_track_map(
    gpx_data: pd.DataFrame,
    stretches: pd.DataFrame,
    wind_direction: float,
    estimated_wind: Optional[float] = None
) -> None:
    """
    Display a map of the track with colored segments based on wind angles.
    
    Args:
        gpx_data: DataFrame with track data
        stretches: DataFrame with sailing segments
        wind_direction: Wind direction in degrees
        estimated_wind: Estimated wind direction (if available)
    """
    if gpx_data.empty:
        st.warning("No track data to display")
        return

    try:
        # Create a base map centered on the track
        mean_lat = gpx_data['latitude'].mean()
        mean_lon = gpx_data['longitude'].mean()
        
        # Find the bounding box to determine best zoom level
        min_lat, max_lat = gpx_data['latitude'].min(), gpx_data['latitude'].max()
        min_lon, max_lon = gpx_data['longitude'].min(), gpx_data['longitude'].max()
        
        # Create the map with auto zoom
        m = folium.Map(location=[mean_lat, mean_lon])
        
        # Fit bounds to the track data
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
        
        # Add the full track as a gray line
        track_points = gpx_data[['latitude', 'longitude']].values.tolist()
        folium.PolyLine(
            track_points,
            color='gray',
            weight=2,
            opacity=0.7,
            tooltip='Full track'
        ).add_to(m)
        
        # Add markers for start and end
        folium.Marker(
            track_points[0],
            icon=folium.Icon(color='green', icon='play', prefix='fa'),
            tooltip='Start'
        ).add_to(m)
        
        folium.Marker(
            track_points[-1],
            icon=folium.Icon(color='red', icon='stop', prefix='fa'),
            tooltip='End'
        ).add_to(m)
        
        # Add colored segments based on wind angles if available
        if not stretches.empty and 'sailing_type' in stretches.columns:
            # Define colors for different sailing types
            colors = {
                'Upwind Port': 'blue',
                'Upwind Starboard': 'purple',
                'Downwind Port': 'orange',
                'Downwind Starboard': 'red'
            }
            
            # Group segments by sailing type
            for sailing_type, color in colors.items():
                type_segments = stretches[stretches['sailing_type'] == sailing_type]
                
                # Add each segment as a colored line
                for _, segment in type_segments.iterrows():
                    start_idx = int(segment['start_idx'])
                    end_idx = int(segment['end_idx'])
                    segment_points = gpx_data.iloc[start_idx:end_idx+1][['latitude', 'longitude']].values.tolist()
                    
                    # Add the segment line
                    if len(segment_points) >= 2:
                        folium.PolyLine(
                            segment_points,
                            color=color,
                            weight=4,
                            opacity=0.8,
                            tooltip=f"{sailing_type}: {segment['angle_to_wind']:.1f}°, {segment['speed']:.1f} knots"
                        ).add_to(m)
        
        # Add wind direction arrow
        if wind_direction is not None:
            # Calculate arrow endpoint
            arrow_length = 0.003  # Arrow length in degrees
            arrow_lat = mean_lat
            arrow_lon = mean_lon
            
            # Calculate endpoint based on wind direction
            end_lat = arrow_lat + arrow_length * np.cos(np.radians(wind_direction))
            end_lon = arrow_lon + arrow_length * np.sin(np.radians(wind_direction))
            
            # Add wind direction arrow
            folium.PolyLine(
                [(arrow_lat, arrow_lon), (end_lat, end_lon)],
                color='black',
                weight=3,
                opacity=0.9,
                tooltip=f"Wind direction: {wind_direction:.1f}°",
                arrow_head=10
            ).add_to(m)
            
            # Add marker with wind info
            wind_info = f"Wind: {wind_direction:.1f}°"
            if estimated_wind is not None and abs(estimated_wind - wind_direction) > 5:
                wind_info += f" (Estimated: {estimated_wind:.1f}°)"
                
            folium.Marker(
                [arrow_lat, arrow_lon],
                icon=folium.DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(75, 18),
                    html=f'<div style="font-size: 12pt; color: var(--text-color, black); background-color: var(--secondary-background-color, rgba(255,255,255,0.7)); '
                         f'padding: 3px; border-radius: 3px;">{wind_info}</div>'
                )
            ).add_to(m)
        
        # Display the map
        folium_static(m, width=800)
        
    except Exception as e:
        logger.error(f"Error displaying track map: {e}")
        st.error(f"Error displaying map: {e}")

def plot_polar_diagram(stretches: pd.DataFrame, wind_direction: float) -> Figure:
    """
    Create a polar diagram showing sailing performance at different wind angles.
    
    Args:
        stretches: DataFrame with sailing segments
        wind_direction: Wind direction in degrees
        
    Returns:
        Figure: Matplotlib figure with the polar plot
    """
    # Create figure
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')
    
    # Get port and starboard data to ensure proper positioning
    port_mask = stretches['tack'] == 'Port'
    starboard_mask = stretches['tack'] == 'Starboard'
    
    # Prepare plotting data for port and starboard, placing them on opposite sides
    port_angles_rad = np.radians(stretches.loc[port_mask, 'angle_to_wind'].values)
    port_speeds = stretches.loc[port_mask, 'speed'].values
    
    starboard_angles_rad = np.radians(stretches.loc[starboard_mask, 'angle_to_wind'].values)
    starboard_speeds = stretches.loc[starboard_mask, 'speed'].values
    
    # Set plot parameters
    ax.set_theta_zero_location("N")  # 0 is at the top
    ax.set_theta_direction(-1)      # Clockwise
    
    # Set fixed max speed for consistent scale
    max_speed = max(stretches['speed'].max() if not stretches.empty else 20, 20)
    
    # Plot segments as points with different colors for port and starboard
    port_colors = []
    for sailing_type in stretches.loc[port_mask, 'sailing_type']:
        if 'Upwind' in sailing_type:
            port_colors.append('blue')
        else:
            port_colors.append('orange')
            
    starboard_colors = []
    for sailing_type in stretches.loc[starboard_mask, 'sailing_type']:
        if 'Upwind' in sailing_type:
            starboard_colors.append('purple')
        else:
            starboard_colors.append('red')
    
    # Scatter plot of port tack points
    if len(port_angles_rad) > 0:
        ax.scatter(port_angles_rad, port_speeds, c=port_colors, s=50, alpha=0.7)
    
    # Scatter plot of starboard tack points
    if len(starboard_angles_rad) > 0:
        ax.scatter(starboard_angles_rad, starboard_speeds, c=starboard_colors, s=50, alpha=0.7)
    
    # Add grid lines and labels
    ax.set_rticks([5, 10, 15, 20, 25])
    ax.set_rlabel_position(90)
    ax.set_rlim(0, max_speed * 1.1)
    
    # Add angle labels
    angle_labels = ['0°\n(upwind)', '30°', '60°', '90°\n(across)', '120°', '150°', '180°\n(downwind)']
    angles_pos = np.radians([0, 30, 60, 90, 120, 150, 180])
    ax.set_xticks(angles_pos)
    ax.set_xticklabels(angle_labels)
    
    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Upwind Port'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='purple', markersize=10, label='Upwind Starboard'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Downwind Port'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Downwind Starboard')
    ]
    ax.legend(handles=legend_elements, loc='lower right', bbox_to_anchor=(0.95, -0.05))
    
    # Add title
    ax.set_title('Sailing Performance by Wind Angle', pad=20)
    
    # Add speed axis label
    fig.text(0.5, 0.04, 'Speed (knots)', ha='center')
    
    # Add wind direction annotation
    fig.text(0.5, 0.97, f'Wind Direction: {wind_direction:.1f}°', ha='center')
    
    # Make full 360° view
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    
    plt.tight_layout()
    return fig