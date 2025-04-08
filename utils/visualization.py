import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

def display_track_map(gpx_data, stretches, wind_direction, estimated_wind=None, selected_segments=None):
    """
    Display a map with color-coded track segments that allows segment selection.
    
    Parameters:
    - gpx_data: DataFrame with track data
    - stretches: DataFrame with segment data
    - wind_direction: Wind direction in degrees
    - estimated_wind: Estimated wind direction (optional)
    - selected_segments: List of segment IDs that are currently selected
    
    Returns:
    - List of selected segment IDs
    """
    import json
    import streamlit as st
    import streamlit.components.v1 as components
    
    # Use selected_segments from session state if not provided
    if selected_segments is None and 'selected_segments' in st.session_state:
        selected_segments = st.session_state.selected_segments
    elif selected_segments is None:
        selected_segments = stretches.index.tolist()  # Default to all selected
    
    # Create the map
    m = folium.Map()
    
    # Add the full track in light gray
    full_track = list(zip(gpx_data['latitude'], gpx_data['longitude']))
    folium.PolyLine(full_track, color='lightgray', weight=2, opacity=0.7).add_to(m)
    
    # Define colors for different sailing types
    colors = {
        'Upwind Port': '#FF0000',       # Red
        'Upwind Starboard': '#0000FF',  # Blue
        'Downwind Port': '#FF8C00',     # Orange
        'Downwind Starboard': '#800080' # Purple
    }
    
    # Add each consistent stretch with color coding
    for idx, stretch in stretches.iterrows():
        start_idx = stretch['start_idx']
        end_idx = stretch['end_idx']
        
        # Get segment points
        segment = gpx_data.iloc[start_idx:end_idx+1]
        track_segment = list(zip(segment['latitude'], segment['longitude']))
        
        sailing_type = stretch['sailing_type']
        color = colors.get(sailing_type, 'green')
        is_selected = idx in selected_segments
        is_suspicious = float(stretch['angle_to_wind']) < 15
        
        # Set appearance based on selection and suspiciousness
        weight = 5 if is_selected else 2
        opacity = 0.9 if is_selected else 0.4
        
        # Different styles for suspicious segments
        dash_array = None
        if is_suspicious:
            dash_array = "5, 5"
        
        tooltip = (f"{sailing_type}: {stretch['bearing']:.1f}° " 
                 f"(Wind angle: {stretch['angle_to_wind']:.1f}°, "
                 f"Speed: {stretch['speed']:.1f} knots)")
        
        if is_suspicious:
            tooltip += "\n⚠️ SUSPICIOUS ANGLE"
        
        folium.PolyLine(
            track_segment, 
            color=color, 
            weight=weight, 
            opacity=opacity,
            tooltip=tooltip,
            dash_array=dash_array
        ).add_to(m)
    
    # Calculate center of the map
    center_lat = gpx_data['latitude'].mean()
    center_lon = gpx_data['longitude'].mean()
    
    # Add wind direction marker - correctly showing the FROM direction
    arrow_html = f'''
    <div style="position: relative; width: 80px; height: 80px;">
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                  display: flex; justify-content: center; align-items: center;">
            <div style="font-weight: bold; position: absolute; top: -20px; text-align: center; width: 100%;">
                WIND {wind_direction}°
            </div>
            <div style="transform: rotate({wind_direction}deg); font-size: 30px;">
                ⬇
            </div>
        </div>
    </div>
    '''
    
    folium.Marker(
        [center_lat, center_lon],
        icon=folium.DivIcon(
            icon_size=(80, 80),
            icon_anchor=(40, 40),
            html=arrow_html
        )
    ).add_to(m)
    
    # Add estimated wind direction if available
    if estimated_wind is not None:
        est_arrow_html = f'''
        <div style="position: relative; width: 80px; height: 80px;">
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                      display: flex; justify-content: center; align-items: center;">
                <div style="font-weight: bold; position: absolute; top: -20px; text-align: center; width: 100%; color: #008800;">
                    EST {estimated_wind:.1f}°
                </div>
                <div style="transform: rotate({estimated_wind}deg); font-size: 30px; color: #008800;">
                    ⬇
                </div>
            </div>
        </div>
        '''
        
        # Place the estimated wind marker slightly offset from the center
        offset_lat = center_lat + 0.001
        offset_lon = center_lon + 0.001
        
        folium.Marker(
            [offset_lat, offset_lon],
            icon=folium.DivIcon(
                icon_size=(80, 80),
                icon_anchor=(40, 40),
                html=est_arrow_html
            )
        ).add_to(m)
    
    # Fit the map to the track
    sw = gpx_data[['latitude', 'longitude']].min().values.tolist()
    ne = gpx_data[['latitude', 'longitude']].max().values.tolist()
    m.fit_bounds([sw, ne])
    
    # Add a more compact legend in a proper position
    legend_html = f'''
    <div style="position: absolute; top: 10px; right: 10px; z-index: 1000; background-color: white; 
    padding: 10px; border: 2px solid grey; border-radius: 5px; max-width: 300px; font-size: 12px;">
    <p style="font-weight: bold; margin: 0 0 5px 0;">Legend</p>
    <div style="display: grid; grid-template-columns: auto auto; grid-gap: 5px; margin-bottom: 5px;">
        <span><i style="background: #FF0000; width: 20px; height: 4px; display: inline-block;"></i> Port Upwind</span>
        <span><i style="background: #0000FF; width: 20px; height: 4px; display: inline-block;"></i> Starboard Upwind</span>
        <span><i style="background: #FF8C00; width: 20px; height: 4px; display: inline-block;"></i> Port Downwind</span>
        <span><i style="background: #800080; width: 20px; height: 4px; display: inline-block;"></i> Starboard Downwind</span>
    </div>
    <div style="margin-bottom: 5px;">
        <span><i style="background: lightgray; width: 20px; height: 2px; display: inline-block;"></i> Full Track</span>
        <span style="margin-left: 10px;"><i style="border: 1px dashed gray; width: 20px; height: 0px; display: inline-block;"></i> Suspicious</span>
    </div>
    <p style="margin: 0;"><b>Wind Direction:</b> {wind_direction}°</p>
    {f'<p style="margin: 0;"><b>Estimated Wind:</b> {estimated_wind:.1f}°</p>' if estimated_wind is not None else ''}
    </div>
    '''
    
    # Add the legend to the map
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add a separate info box for wind explanation at the bottom
    info_html = f'''
    <div style="position: absolute; bottom: 10px; left: 10px; z-index: 1000; background-color: white; 
    padding: 10px; border: 2px solid grey; border-radius: 5px; max-width: 300px; font-size: 12px;">
    <p style="font-weight: bold; margin: 0 0 5px 0;">Wind Angles</p>
    <p style="margin: 0 0 5px 0;">Wind angles are degrees <i>off the wind direction</i>:</p>
    <ul style="margin: 0; padding-left: 20px;">
      <li>Upwind: <45° ideal, <90° total</li>
      <li>Downwind: >90° running</li>
      <li>Port/Starboard: tack relative to wind</li>
    </ul>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(info_html))
    
    # We're not using JavaScript for selection since it's not working reliably
    # Instead, we'll rely on the checkbox UI for selection
    
    # Display the map with folium_static - reverting to simpler method for now
    # since the JavaScript interaction isn't working correctly
    folium_static(m, height=600, width=800)
    
    # We don't return anything
    return None

def plot_polar_diagram(stretches, wind_direction):
    """Create a polar plot showing sailing performance at different angles to wind."""
    # Create figure with two subplots side by side
    fig = plt.figure(figsize=(12, 6))
    
    # Get data ready
    port_mask = stretches['tack'] == 'Port'
    starboard_mask = stretches['tack'] == 'Starboard'
    
    # Create a colormap for upwind/downwind
    cmap = LinearSegmentedColormap.from_list(
        'wind_colormap', [(0, 'darkred'), (0.5, 'gold'), (1, 'darkblue')])
    
    # Split the plot into port and starboard sections
    # ===== PORT TACK (LEFT SIDE) =====
    if sum(port_mask) > 0:
        port_data = stretches[port_mask].copy()
        
        # Create left subplot for Port tack (0-180°)
        ax_port = fig.add_subplot(121, projection='polar')
        
        # Get values
        thetas = np.radians(port_data['angle_to_wind'].values)
        r = port_data['speed'].values  # Speed in knots
        weights = port_data['distance'].values
        
        # Normalize weights for scatter size
        norm_weights = 20 * weights / weights.max() + 10 if weights.max() > 0 else 10
        
        # Plot the port tack points
        port_scatter = ax_port.scatter(
            thetas, r, 
            c=port_data['angle_to_wind'], 
            cmap=cmap, s=norm_weights, alpha=0.8, 
            vmin=0, vmax=180, marker='o', edgecolors='darkred'
        )
        
        # Set up the polar plot - 0 degrees at top (upwind)
        ax_port.set_theta_zero_location('N')  # 0 degrees at the top
        ax_port.set_theta_direction(1)  # counter-clockwise (mirror flip)
        
        # Set the theta limits to 0-180 degrees (only show the top half)
        ax_port.set_thetamin(0)
        ax_port.set_thetamax(180)
        
        # Get max speed for consistent scaling and annotations
        max_r_port = max(r) if len(r) > 0 else 1
        
        # Set consistent speed rings
        radii = np.linspace(0, np.ceil(max_r_port), 6)
        ax_port.set_rticks(radii)
        ax_port.set_rlim(0, np.ceil(max_r_port) * 1.1)
        
        # Add important angle reference lines
        angles = [0, 45, 90, 135, 180]
        labels = ["0°", "45°", "90°", "135°", "180°"]
        linestyles = [':', '--', '-', '--', ':']
        colors = ['black', 'red', 'green', 'orange', 'black']
        
        for angle, label, ls, color in zip(angles, labels, linestyles, colors):
            # Add radial lines at important angles
            ax_port.plot([np.radians(angle), np.radians(angle)], [0, max_r_port * 1.1], 
                    ls=ls, color=color, alpha=0.5, linewidth=1)
            
            # Add angle labels just outside the plot
            ax_port.text(np.radians(angle), max_r_port * 1.07, label, 
                    ha='center', va='center', color=color, fontsize=9)
        
        # Add title only - removing the "INTO WIND/DOWNWIND" labels that overlap with other text
        ax_port.set_title('Port Tack', fontweight='bold', pad=15)
    
    # ===== STARBOARD TACK (RIGHT SIDE) =====
    if sum(starboard_mask) > 0:
        starboard_data = stretches[starboard_mask].copy()
        
        # Create right subplot for Starboard tack (0-180°)
        ax_starboard = fig.add_subplot(122, projection='polar')
        
        # Get values
        thetas = np.radians(starboard_data['angle_to_wind'].values)
        r = starboard_data['speed'].values  # Speed in knots
        weights = starboard_data['distance'].values
        
        # Normalize weights for scatter size
        norm_weights = 20 * weights / weights.max() + 10 if weights.max() > 0 else 10
        
        # Plot the starboard tack points
        starboard_scatter = ax_starboard.scatter(
            thetas, r, 
            c=starboard_data['angle_to_wind'], 
            cmap=cmap, s=norm_weights, alpha=0.8, 
            vmin=0, vmax=180, marker='s', edgecolors='darkblue'
        )
        
        # Set up the polar plot - 0 degrees at top (upwind)
        ax_starboard.set_theta_zero_location('N')  # 0 degrees at the top
        ax_starboard.set_theta_direction(-1)  # clockwise
        
        # Set the theta limits to 0-180 degrees (only show the top half)
        ax_starboard.set_thetamin(0)
        ax_starboard.set_thetamax(180)
        
        # Get max speed for consistent scaling and annotations
        max_r_starboard = max(r) if len(r) > 0 else 1
        
        # Set consistent speed rings
        radii = np.linspace(0, np.ceil(max_r_starboard), 6)
        ax_starboard.set_rticks(radii)
        ax_starboard.set_rlim(0, np.ceil(max_r_starboard) * 1.1)
        
        # Add important angle reference lines
        angles = [0, 45, 90, 135, 180]
        labels = ["0°", "45°", "90°", "135°", "180°"]
        linestyles = [':', '--', '-', '--', ':']
        colors = ['black', 'red', 'green', 'orange', 'black']
        
        for angle, label, ls, color in zip(angles, labels, linestyles, colors):
            # Add radial lines at important angles
            ax_starboard.plot([np.radians(angle), np.radians(angle)], [0, max_r_starboard * 1.1], 
                    ls=ls, color=color, alpha=0.5, linewidth=1)
            
            # Add angle labels just outside the plot
            ax_starboard.text(np.radians(angle), max_r_starboard * 1.07, label, 
                    ha='center', va='center', color=color, fontsize=9)
        
        # Add title only - removing the "INTO WIND/DOWNWIND" labels that overlap with other text
        ax_starboard.set_title('Starboard Tack', fontweight='bold', pad=15)
    
    # ===== COMMON ELEMENTS =====
    # Set the same scale for both plots if both exist
    if sum(port_mask) > 0 and sum(starboard_mask) > 0:
        max_r_all = max(max_r_port, max_r_starboard)
        radii = np.linspace(0, np.ceil(max_r_all), 6)
        ax_port.set_rticks(radii)
        ax_port.set_rlim(0, np.ceil(max_r_all) * 1.1)
        ax_starboard.set_rticks(radii)
        ax_starboard.set_rlim(0, np.ceil(max_r_all) * 1.1)
        
    # Add colorbar if we have data
    if sum(port_mask) > 0 or sum(starboard_mask) > 0:
        scatter_for_colorbar = port_scatter if sum(port_mask) > 0 else starboard_scatter
        cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])  # [left, bottom, width, height]
        cbar = fig.colorbar(scatter_for_colorbar, cax=cbar_ax)
        cbar.set_label('Angle to Wind (degrees)')
    
    # Add explanatory text with better spacing
    plt.figtext(0.5, 0.03, 
               "These polar plots show your speed (radius) at different angles to the wind.\n" +
               "0° is directly into the wind (top), 90° is across (sides), 180° is directly downwind (bottom).\n" +
               "Marker size indicates distance sailed at this angle/speed combination.",
               ha='center', fontsize=9, wrap=True)
    
    # Adjust layout - increase bottom margin to give text more room and bring plots closer
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.17, right=0.85, wspace=-0.45)
    
    return fig

def plot_bearing_distribution(stretches, wind_direction):
    """Create histogram showing distribution of sailing directions."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Define colors for different sailing types
    colors = {
        'Upwind Port': '#FF0000',       # Red
        'Upwind Starboard': '#0000FF',  # Blue
        'Downwind Port': '#FF8C00',     # Orange
        'Downwind Starboard': '#800080' # Purple
    }
    
    # Group by sailing type for stacked histogram
    groups = stretches.groupby('sailing_type')
    
    # Create bins for the histogram
    bins = np.linspace(0, 360, 37)  # 36 bins of 10 degrees each
    
    # Plot stacked histogram
    for name, group in groups:
        ax.hist(group['bearing'], bins=bins, weights=group['distance'],
               label=name, alpha=0.7, edgecolor='black',
               color=colors.get(name, 'skyblue'))
    
    # Add wind direction line
    ax.axvline(x=wind_direction, color='black', linestyle='--', linewidth=2, 
               label=f'Wind Direction ({wind_direction}°)')
    
    # Add opposite wind direction line
    opposite_wind = (wind_direction + 180) % 360
    ax.axvline(x=opposite_wind, color='green', linestyle='--', linewidth=2,
               label=f'Downwind ({opposite_wind}°)')
    
    # Add 45° lines from wind direction (typical sailing angles)
    upwind_port = (wind_direction - 45) % 360
    upwind_starboard = (wind_direction + 45) % 360
    downwind_port = (wind_direction - 135) % 360
    downwind_starboard = (wind_direction + 135) % 360
    
    plt.axvline(x=upwind_port, color='red', linestyle=':', linewidth=1, 
               label=f'45° Port ({upwind_port}°)')
    plt.axvline(x=upwind_starboard, color='blue', linestyle=':', linewidth=1, 
               label=f'45° Starboard ({upwind_starboard}°)')
    
    ax.set_xlabel('Bearing (degrees)')
    ax.set_ylabel('Distance (meters)')
    ax.set_title('Distribution of Sailing Directions')
    ax.set_xticks(np.arange(0, 361, 30))
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    return fig