import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from utils.calculations import calculate_bearing, calculate_distance, angle_to_wind

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
    
    df = df.copy()
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
                        'duration': duration,
                        'speed': total_distance / duration if duration > 0 else 0
                    })
            
            # Start new stretch
            current_stretch = {'start_idx': i, 'start_time': df.iloc[i]['time'], 'bearing': df.iloc[i]['bearing']}
    
    # Check if the last stretch meets criteria
    if len(df) > 0:
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
                'duration': duration,
                'speed': total_distance / duration if duration > 0 else 0
            })
            
    if stretches and len(stretches) > 0:
        result_df = pd.DataFrame(stretches)
        # Convert speed from m/s to knots (1 m/s = 1.94384 knots)
        result_df['speed'] = result_df['speed'] * 1.94384
        return result_df
    
    return pd.DataFrame(stretches)
    
    return pd.DataFrame(stretches)

def analyze_wind_angles(stretches, wind_direction):
    """Calculate angles relative to wind and determine tack."""
    if stretches.empty:
        return stretches
    
    # Make a copy to avoid modifying the original
    result = stretches.copy()
    
    # Calculate angles relative to wind
    result['angle_to_wind'] = result['bearing'].apply(
        lambda x: angle_to_wind(x, wind_direction))
    
    # Determine if upwind/downwind and tack
    result['tack'] = result['bearing'].apply(
        lambda x: 'Port' if (x - wind_direction) % 360 <= 180 else 'Starboard')
    
    result['upwind_downwind'] = result.apply(
        lambda row: 'Upwind' if row['angle_to_wind'] < 90 else 'Downwind', axis=1)
    
    # Create combined category for coloring
    result['sailing_type'] = result.apply(
        lambda row: f"{row['upwind_downwind']} {row['tack']}", axis=1)
    
    return result

def estimate_wind_direction(stretches):
    """Estimate wind direction based on sailing patterns."""
    if len(stretches) < 3:
        return None
    
    # Filter to stretches with good distance
    min_distance_threshold = stretches['distance'].quantile(0.5)  # Use median as threshold
    good_stretches = stretches[stretches['distance'] > min_distance_threshold]
    
    if len(good_stretches) < 3:
        return None
    
    # Try to identify upwind tacks by finding clusters of bearings
    bearings = good_stretches['bearing'].values
    
    # Convert bearings to x,y coordinates on unit circle for proper clustering
    x = np.cos(np.radians(bearings))
    y = np.sin(np.radians(bearings))
    
    # Try to find 2-4 clusters (usually upwind port/starboard, downwind port/starboard)
    best_score = -1
    best_n = 2
    best_kmeans = None
    
    for n in range(2, min(5, len(good_stretches))):
        kmeans = KMeans(n_clusters=n, random_state=0, n_init=10).fit(np.column_stack([x, y]))
        score = kmeans.inertia_
        if best_score == -1 or score < best_score * 0.7:  # Significant improvement
            best_score = score
            best_n = n
            best_kmeans = kmeans
    
    # Get cluster centers and convert back to angles
    centers = best_kmeans.cluster_centers_
    center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) + 360) % 360
    
    # Get the two most opposite angles (likely upwind tacks)
    max_diff = -1
    angle1 = angle2 = 0
    
    for i in range(len(center_angles)):
        for j in range(i+1, len(center_angles)):
            diff = abs(center_angles[i] - center_angles[j])
            diff = min(diff, 360 - diff)
            if diff > max_diff:
                max_diff = diff
                angle1 = center_angles[i]
                angle2 = center_angles[j]
    
    # If we found a reasonable pair (at least 60° apart)
    if max_diff > 60:
        # Calculate the average heading between the two opposite tacks
        avg_heading = (angle1 + angle2) / 2
        # The wind direction is perpendicular to this heading
        estimated_wind = (avg_heading + 90) % 360
        
        return estimated_wind
    
    return None