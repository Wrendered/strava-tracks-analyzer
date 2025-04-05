import streamlit as st
import gpxpy
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
from geopy.distance import geodesic
import math
from datetime import timedelta

def load_gpx_file(gpx_file):
    """Parse a GPX file and return track data as a DataFrame."""
    gpx = gpxpy.parse(gpx_file)
    
    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'time': point.time,
                })
    
    return pd.DataFrame(data)

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate the bearing between two points in degrees."""
    # Convert to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    # Calculate bearing
    x = math.sin(lon2 - lon1) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    initial_bearing = math.atan2(x, y)
    
    # Convert to degrees
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    
    return compass_bearing

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters."""
    return geodesic((lat1, lon1), (lat2, lon2)).meters

def find_consistent_angle_stretches(df, angle_tolerance, min_duration_seconds, min_distance_meters):
    """Find stretches of consistent sailing angle."""
    if len(df) < 2:
        return pd.DataFrame()
    
    # Calculate bearing and distance for each point
    bearings = []
    distances = []
    durations = []
    
    for i in range(len(df) - 1):
        lat1, lon1 = df.iloc[i]['latitude'], df.iloc[i]['longitude']
        lat2, lon2 = df.iloc[i+1]['latitude'], df.iloc[i+1]['longitude']
        
        bearing = calculate_bearing(lat1, lon1, lat2, lon2)
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        
        bearings.append(bearing)
        distances.append(distance)
        
        if i > 0 and 'time' in df.columns and df.iloc[i]['time'] is not None and df.iloc[i-1]['time'] is not None:
            duration = (df.iloc[i]['time'] - df.iloc[i-1]['time']).total_seconds()
            durations.append(duration)
        else:
            durations.append(0)
    
    # Add one more to match length of dataframe
    bearings.append(bearings[-1] if bearings else 0)
    distances.append(distances[-1] if distances else 0)
    durations.append(durations[-1] if durations else 0)
    
    df['bearing'] = bearings
    df['distance_m'] = distances
    df['duration_sec'] = durations
    
    # Find stretches of consistent angle
    stretches = []
    current_stretch = {'start_idx': 0, 'start_time': df.iloc[0]['time'], 'bearing': bearings[0]}
    
    for i in range(1, len(df)):
        angle_diff = min((df.iloc[i]['bearing'] - current_stretch['bearing']) % 360, 
                         (current_stretch['bearing'] - df.iloc[i]['bearing']) % 360)
        
        if angle_diff > angle_tolerance:
            # End of stretch
            end_idx = i - 1
            if end_idx > current_stretch['start_idx']:
                stretch_df = df.iloc[current_stretch['start_idx']:end_idx+1]
                total_distance = stretch_df['distance_m'].sum()
                if 'time' in df.columns and df.iloc[end_idx]['time'] is not None and current_stretch['start_time'] is not None:
                    duration = (df.iloc[end_idx]['time'] - current_stretch['start_time']).total_seconds()
                else:
                    duration = 0
                
                # Only add if meets BOTH minimum criteria
                if duration >= min_duration_seconds and total_distance >= min_distance_meters:
                    stretches.append({
                        'start_idx': current_stretch['start_idx'],
                        'end_idx': end_idx,
                        'bearing': current_stretch['bearing'],
                        'distance': total_distance,
                        'duration': duration
                    })
            
            # Start new stretch
            current_stretch = {'start_idx': i, 'start_time': df.iloc[i]['time'], 'bearing': df.iloc[i]['bearing']}
    
    # Check if the last stretch meets criteria
    if 'time' in df.columns and df.iloc[-1]['time'] is not None and current_stretch['start_time'] is not None:
        duration = (df.iloc[-1]['time'] - current_stretch['start_time']).total_seconds()
    else:
        duration = 0
    
    stretch_df = df.iloc[current_stretch['start_idx']:]
    total_distance = stretch_df['distance_m'].sum()
    
    # Only add if meets BOTH minimum criteria
    if duration >= min_duration_seconds and total_distance >= min_distance_meters:
        stretches.append({
            'start_idx': current_stretch['start_idx'],
            'end_idx': len(df) - 1,
            'bearing': current_stretch['bearing'],
            'distance': total_distance,
            'duration': duration
        })
    
    return pd.DataFrame(stretches)

def angle_to_wind(bearing, wind_direction):
    """Calculate angle relative to the wind direction."""
    diff = abs(bearing - wind_direction)
    return min(diff, 360 - diff)

def main():
    st.title("Wingfoil Track Analyzer")
    
    # Session parameters
    with st.sidebar:
        st.header("Analysis Parameters")
        wind_direction = st.number_input("Estimated Wind Direction (degrees)", 
                                          min_value=0, max_value=359, value=90,
                                          help="Direction the wind is coming FROM (e.g., 90° for East wind)")
        
        angle_tolerance = st.slider("Angle Tolerance (degrees)", 
                                    min_value=1, max_value=20, value=5)
        
        # Both time AND distance required
        min_duration = st.slider("Minimum Duration (seconds)", 
                                min_value=1, max_value=60, value=5)
        
        min_distance = st.slider("Minimum Distance (meters)", 
                                min_value=5, max_value=200, value=10)
    
    uploaded_file = st.file_uploader("Upload a GPX file", type=['gpx'])
    
    if uploaded_file is not None:
        # Read the GPX file
        gpx_data = load_gpx_file(uploaded_file)
        
        # Display basic stats
        st.subheader("Track Stats")
        if not gpx_data.empty:
            if 'time' in gpx_data and gpx_data['time'].notna().any():
                start_time = gpx_data['time'].min()
                end_time = gpx_data['time'].max()
                duration = end_time - start_time
                st.write(f"Date: {start_time.date()}")
                st.write(f"Duration: {duration}")
            
            # Calculate total distance
            if len(gpx_data) > 1:
                distance = 0
                for i in range(len(gpx_data) - 1):
                    point1 = (gpx_data.iloc[i]['latitude'], gpx_data.iloc[i]['longitude'])
                    point2 = (gpx_data.iloc[i+1]['latitude'], gpx_data.iloc[i+1]['longitude'])
                    distance += geodesic(point1, point2).kilometers
                
                st.write(f"Total Distance: {distance:.2f} km")
            
            # Find stretches of consistent angle
            stretches = find_consistent_angle_stretches(gpx_data, 
                                                      angle_tolerance,
                                                      min_duration, 
                                                      min_distance)
            
            if not stretches.empty:
                # Calculate angles relative to wind
                stretches['angle_to_wind'] = stretches['bearing'].apply(
                    lambda x: angle_to_wind(x, wind_direction))
                
                # Determine if upwind/downwind
                stretches['tack'] = stretches['bearing'].apply(
                    lambda x: 'Port' if (x - wind_direction) % 360 <= 180 else 'Starboard')
                
                stretches['upwind_downwind'] = stretches.apply(
                    lambda row: 'Upwind' if row['angle_to_wind'] < 90 else 'Downwind', axis=1)
                
                # Display stretches in table
                st.subheader(f"Consistent Angle Stretches (Found: {len(stretches)})")
                
                display_cols = ['bearing', 'angle_to_wind', 'tack', 'upwind_downwind', 
                                'distance', 'duration']
                display_df = stretches[display_cols].copy()
                display_df['bearing'] = display_df['bearing'].round(1)
                display_df['angle_to_wind'] = display_df['angle_to_wind'].round(1)
                display_df['distance'] = display_df['distance'].round(1)
                display_df['duration'] = display_df['duration'].apply(
                    lambda x: str(timedelta(seconds=int(x))))
                
                st.dataframe(display_df)
                
                # Summary statistics
                st.subheader("Angle Analysis")
                
                # Best upwind angles
                upwind = stretches[stretches['angle_to_wind'] < 90].copy()
                if not upwind.empty:
                    port_upwind = upwind[upwind['tack'] == 'Port']
                    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if not port_upwind.empty:
                            best_port = port_upwind.loc[port_upwind['angle_to_wind'].idxmin()]
                            st.metric("Best Port Upwind Angle", f"{best_port['angle_to_wind']:.1f}°")
                    
                    with col2:
                        if not starboard_upwind.empty:
                            best_starboard = starboard_upwind.loc[starboard_upwind['angle_to_wind'].idxmin()]
                            st.metric("Best Starboard Upwind Angle", f"{best_starboard['angle_to_wind']:.1f}°")
                
                # Display map with color-coded stretches
                st.subheader("Track Map")
                m = folium.Map()
                
                # Add the full track in light gray
                full_track = list(zip(gpx_data['latitude'], gpx_data['longitude']))
                folium.PolyLine(full_track, color='lightgray', weight=2, opacity=0.7).add_to(m)
                
                # Add each consistent stretch with color coding
                colors = {
                    'Port Upwind': 'red',
                    'Starboard Upwind': 'blue',
                    'Port Downwind': 'orange',
                    'Starboard Downwind': 'purple'
                }
                
                for _, stretch in stretches.iterrows():
                    segment = gpx_data.iloc[stretch['start_idx']:stretch['end_idx']+1]
                    track_segment = list(zip(segment['latitude'], segment['longitude']))
                    
                    tack = stretch['tack']
                    updown = stretch['upwind_downwind']
                    color_key = f"{tack} {updown}"
                    color = colors.get(color_key, 'green')
                    
                    folium.PolyLine(
                        track_segment, 
                        color=color, 
                        weight=4, 
                        opacity=0.8,
                        tooltip=f"{tack} {updown}: {stretch['bearing']:.1f}° (Wind: {stretch['angle_to_wind']:.1f}°)"
                    ).add_to(m)
                
                # Add wind direction arrow at center of map
                center_lat = gpx_data['latitude'].mean()
                center_lon = gpx_data['longitude'].mean()
                
                folium.Marker(
                    [center_lat, center_lon],
                    icon=folium.DivIcon(
                        icon_size=(150,36),
                        icon_anchor=(75,18),
                        html=f'<div style="font-size: 12pt; color: black;">Wind: {wind_direction}°</div>'
                    )
                ).add_to(m)
                
                # Fit the map to the track
                sw = gpx_data[['latitude', 'longitude']].min().values.tolist()
                ne = gpx_data[['latitude', 'longitude']].max().values.tolist()
                m.fit_bounds([sw, ne])
                
                # Add legend
                legend_html = '''
                <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; 
                padding: 10px; border: 2px solid grey; border-radius: 5px;">
                <p><b>Legend</b></p>
                <p><i style="background: red; width: 20px; height: 2px; display: inline-block;"></i> Port Upwind</p>
                <p><i style="background: blue; width: 20px; height: 2px; display: inline-block;"></i> Starboard Upwind</p>
                <p><i style="background: orange; width: 20px; height: 2px; display: inline-block;"></i> Port Downwind</p>
                <p><i style="background: purple; width: 20px; height: 2px; display: inline-block;"></i> Starboard Downwind</p>
                <p><i style="background: lightgray; width: 20px; height: 2px; display: inline-block;"></i> Full Track</p>
                </div>
                '''
                m.get_root().html.add_child(folium.Element(legend_html))
                
                # Display the map
                folium_static(m)
                
                # Plot bearing distribution
                st.subheader("Bearing Distribution")
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Calculate histogram data - using bearings from each point, weighted by distance
                hist_data = []
                weights = []
                
                for _, stretch in stretches.iterrows():
                    hist_data.append(stretch['bearing'])
                    weights.append(stretch['distance'])
                
                ax.hist(hist_data, bins=36, range=(0, 360), weights=weights, color='skyblue', edgecolor='black')
                
                # Add wind direction line
                plt.axvline(x=wind_direction, color='r', linestyle='--', label=f'Wind Direction ({wind_direction}°)')
                
                # Add opposite wind direction line
                opposite_wind = (wind_direction + 180) % 360
                plt.axvline(x=opposite_wind, color='g', linestyle='--', label=f'Downwind ({opposite_wind}°)')
                
                ax.set_xlabel('Bearing (degrees)')
                ax.set_ylabel('Distance (meters)')
                ax.set_title('Distribution of Sailing Directions')
                ax.set_xticks(np.arange(0, 361, 30))
                ax.legend()
                ax.grid(True)
                
                st.pyplot(fig)
            else:
                st.warning("No consistent angle stretches found with current parameters. Try adjusting tolerance or minimum duration/distance.")
        else:
            st.error("Unable to parse GPX data. Please check the file format.")

if __name__ == "__main__":
    main()