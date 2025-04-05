import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

def display_track_map(gpx_data, stretches, wind_direction, estimated_wind=None):
    """Display a map with color-coded track segments."""
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
    for _, stretch in stretches.iterrows():
        start_idx = stretch['start_idx']
        end_idx = stretch['end_idx']
        
        # Get segment points
        segment = gpx_data.iloc[start_idx:end_idx+1]
        track_segment = list(zip(segment['latitude'], segment['longitude']))
        
        sailing_type = stretch['sailing_type']
        color = colors.get(sailing_type, 'green')
        
        tooltip = (f"{sailing_type}: {stretch['bearing']:.1f}° " 
                 f"(Wind angle: {stretch['angle_to_wind']:.1f}°, "
                 f"Speed: {stretch['speed']:.1f} knots)")
        
        folium.PolyLine(
            track_segment, 
            color=color, 
            weight=4, 
            opacity=0.8,
            tooltip=tooltip
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
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; 
    padding: 10px; border: 2px solid grey; border-radius: 5px;">
    <p><b>Legend</b></p>
    <p><i style="background: #FF0000; width: 20px; height: 4px; display: inline-block;"></i> Port Upwind</p>
    <p><i style="background: #0000FF; width: 20px; height: 4px; display: inline-block;"></i> Starboard Upwind</p>
    <p><i style="background: #FF8C00; width: 20px; height: 4px; display: inline-block;"></i> Port Downwind</p>
    <p><i style="background: #800080; width: 20px; height: 4px; display: inline-block;"></i> Starboard Downwind</p>
    <p><i style="background: lightgray; width: 20px; height: 2px; display: inline-block;"></i> Full Track</p>
    <p><b>Wind Direction:</b> {wind_direction}°</p>
    {f'<p><b>Estimated Wind:</b> {estimated_wind:.1f}°</p>' if estimated_wind is not None else ''}
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Display the map
    folium_static(m)

def plot_polar_diagram(stretches, wind_direction):
    """Create a polar plot showing sailing angles relative to wind."""
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    
    # Convert to polar coordinates (r=speed, theta=angle to wind)
    thetas = np.radians(stretches['angle_to_wind'].values)
    r = stretches['speed'].values  # Speed is now in knots
    weights = stretches['distance'].values
    
    # Normalize weights for scatter size
    norm_weights = 20 * weights / weights.max() + 5 if weights.max() > 0 else 5
    
    # Create a colormap: red for upwind, blue for downwind
    cmap = LinearSegmentedColormap.from_list(
        'wind_colormap', [(0, 'darkred'), (0.5, 'gold'), (1, 'darkblue')])
    
    # Plot points
    scatter = ax.scatter(thetas, r, c=stretches['angle_to_wind'], 
               cmap=cmap, s=norm_weights, alpha=0.7, 
               vmin=0, vmax=180)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
    cbar.set_label('Angle to Wind (degrees)')
    
    # Set up the polar plot - 0 degrees is TO WIND (not North)
    ax.set_theta_zero_location('N')  # 0 degrees at the top
    ax.set_theta_direction(-1)  # clockwise
    
    # Add wind direction label
    ax.text(0, -0.1, "INTO WIND", ha='center', va='center', transform=ax.transAxes, fontweight='bold')
    ax.text(0.5, -0.1, "DOWNWIND", ha='center', va='center', transform=ax.transAxes, fontweight='bold')
    
    # Add radial labels (speed in knots)
    if len(r) > 0:
        max_r = max(r)
        radii = np.linspace(0, max(1, round(max_r)), 5)
        ax.set_rticks(radii)
        ax.set_rlabel_position(45)
        ax.set_rlim(0, max_r * 1.1)
        ax.grid(True)
    
    ax.set_title('Polar Performance Plot (Speed in Knots)', va='bottom')
    plt.tight_layout()
    
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