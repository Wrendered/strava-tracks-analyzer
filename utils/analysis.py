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
        
        # Log the found stretches for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Found {len(result_df)} stretches with bearings: {result_df['bearing'].tolist()}")
        
        return result_df
    
    # Create empty DataFrame with correct columns if no stretches
    return pd.DataFrame(columns=['start_idx', 'end_idx', 'bearing', 'distance', 'duration', 'speed'])

def analyze_wind_angles(stretches, wind_direction):
    """Calculate angles relative to wind and determine tack."""
    if stretches.empty:
        return stretches
    
    # Make a copy to avoid modifying the original
    result = stretches.copy()
    
    # Add the wind direction for reference
    result['wind_direction'] = wind_direction
    
    # Calculate angles relative to wind
    result['angle_to_wind'] = result['bearing'].apply(
        lambda x: angle_to_wind(x, wind_direction))
    
    # Determine tack based on bearing relative to wind direction
    result['tack'] = result['bearing'].apply(
        lambda x: 'Port' if (x - wind_direction) % 360 <= 180 else 'Starboard')
    
    # Determine upwind vs downwind based on angle to wind
    result['upwind_downwind'] = result.apply(
        lambda row: 'Upwind' if row['angle_to_wind'] < 90 else 'Downwind', axis=1)
    
    # Create combined category for coloring and display
    result['sailing_type'] = result.apply(
        lambda row: f"{row['upwind_downwind']} {row['tack']}", axis=1)
    
    # Add debug info to help verify calculations
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Wind direction: {wind_direction}°")
    
    # Log a summary of the tacks
    port_count = sum(result['tack'] == 'Port')
    stbd_count = sum(result['tack'] == 'Starboard')
    upwind_count = sum(result['upwind_downwind'] == 'Upwind')
    downwind_count = sum(result['upwind_downwind'] == 'Downwind')
    
    logger.info(f"Tack summary: {port_count} Port, {stbd_count} Starboard")
    logger.info(f"Direction summary: {upwind_count} Upwind, {downwind_count} Downwind")
    
    return result

def estimate_wind_direction(stretches, use_simple_method=True):
    """
    Estimate wind direction based on sailing patterns.
    
    Uses multiple methods and heuristics to estimate the wind direction:
    1. Clustering bearings to find opposite tacks
    2. Assuming most sailing is across the wind (90° from wind)
    3. Finding the most frequent sailing directions
    
    Parameters:
    - stretches: DataFrame of consistent sailing segments
    - use_simple_method: If True, uses the simpler and more reliable 
      method of directly clustering possible wind directions (works 
      well for most real-world tracks)
    """
    if len(stretches) < 3:
        return None
    
    # Filter to stretches with good distance and speed
    min_distance_threshold = stretches['distance'].quantile(0.25)  # Lower threshold to include more data
    good_stretches = stretches[stretches['distance'] > min_distance_threshold]
    
    # Sort by distance to prioritize longer stretches in analysis
    good_stretches = good_stretches.sort_values('distance', ascending=False)
    
    if len(good_stretches) < 3:
        return None
    
    # Get the bearings from good stretches
    bearings = good_stretches['bearing'].values
    
    # Method 1: Clustering approach (find most opposite angles)
    # Convert bearings to x,y coordinates on unit circle for proper clustering
    x = np.cos(np.radians(bearings))
    y = np.sin(np.radians(bearings))
    
    # Try different numbers of clusters to find the best fit
    best_n = min(4, len(good_stretches) - 1)  # Cap at 4 clusters or n-1
    
    # Use best_n clusters directly instead of trying to determine it dynamically
    kmeans = KMeans(n_clusters=best_n, random_state=0, n_init=10).fit(np.column_stack([x, y]))
    
    # Get cluster centers and convert back to angles
    centers = kmeans.cluster_centers_
    center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) + 360) % 360
    
    # Count the number of points in each cluster
    cluster_counts = [np.sum(kmeans.labels_ == i) for i in range(len(center_angles))]
    
    # Find the two most populated clusters that are sufficiently opposite
    # Sort clusters by population
    sorted_clusters = sorted(range(len(cluster_counts)), key=lambda i: cluster_counts[i], reverse=True)
    
    # Find the most opposite pair among the top 3 most populated clusters
    top_clusters = sorted_clusters[:min(3, len(sorted_clusters))]
    max_diff = -1
    angle1 = angle2 = 0
    
    for i in range(len(top_clusters)):
        for j in range(i+1, len(top_clusters)):
            idx1 = top_clusters[i]
            idx2 = top_clusters[j]
            angle_i = center_angles[idx1]
            angle_j = center_angles[idx2]
            diff = abs(angle_i - angle_j)
            diff = min(diff, 360 - diff)
            if diff > max_diff:
                max_diff = diff
                angle1 = angle_i
                angle2 = angle_j
    
    # Method 2: Analyze possible wind directions perpendicular to bearings
    # Generate possible wind directions from each bearing
    all_possible_winds = []
    for bearing in bearings:
        all_possible_winds.append((bearing + 90) % 360)  # Wind from right
        all_possible_winds.append((bearing - 90) % 360)  # Wind from left
    
    # Cluster the possible wind angles
    x_wind = np.cos(np.radians(all_possible_winds))
    y_wind = np.sin(np.radians(all_possible_winds))
    kmeans_wind = KMeans(n_clusters=2, random_state=0, n_init=10).fit(np.column_stack([x_wind, y_wind]))
    
    # Get the cluster centers
    centers_wind = kmeans_wind.cluster_centers_
    center_angles_wind = (np.degrees(np.arctan2(centers_wind[:, 1], centers_wind[:, 0])) + 360) % 360
    
    # Count the number of points in each cluster
    cluster_counts_wind = [np.sum(kmeans_wind.labels_ == i) for i in range(len(center_angles_wind))]
    
    # The most populated cluster is likely the true wind direction
    best_cluster = np.argmax(cluster_counts_wind)
    method2_wind = center_angles_wind[best_cluster]
    
    # If the clusters are close to equal, consider both
    min_points_ratio = min(cluster_counts_wind) / max(cluster_counts_wind)
    
    # If using simple method, just return method2_wind which is more reliable
    # for real-world sailing tracks (directly clusters possible wind directions)
    if use_simple_method:
        # Simple method works best for real data
        return method2_wind
    
    # Complex logic for combining the methods - works better for synthetic data
    # but can be less reliable for real-world tracks with irregular patterns
    if max_diff > 120:  # We have very opposite tacks - good for method 1
        # Calculate the average heading between the two opposite tacks
        # This needs special handling if angles cross the 0/360 boundary
        if abs(angle1 - angle2) > 180:
            # Adjust one of the angles to handle the boundary crossing
            if angle1 < angle2:
                angle1 += 360
            else:
                angle2 += 360
                
        avg_heading = (angle1 + angle2) / 2
        if avg_heading >= 360:
            avg_heading -= 360
            
        # The wind direction is perpendicular to this heading
        method1_wind = (avg_heading + 90) % 360
        
        # Check how close the two methods are
        wind_diff = min(abs(method1_wind - method2_wind), 360 - abs(method1_wind - method2_wind))
        
        if wind_diff <= 45:
            # Methods agree, use a weighted average favoring method 2
            weight_method1 = 0.3
            weight_method2 = 0.7
            
            # We need to handle the case where methods are on opposite sides of 0/360
            if abs(method1_wind - method2_wind) > 180:
                if method1_wind < method2_wind:
                    method1_wind += 360
                else:
                    method2_wind += 360
                    
            estimated_wind = (method1_wind * weight_method1 + method2_wind * weight_method2) / (weight_method1 + weight_method2)
            if estimated_wind >= 360:
                estimated_wind -= 360
        else:
            # Methods disagree significantly
            # If method 2 is very confident (one cluster much larger than the other), use it
            if min_points_ratio < 0.3:
                estimated_wind = method2_wind
            else:
                # Otherwise, weakly prefer method 1
                estimated_wind = method1_wind
    elif max_diff > 90:  # Good but not ideal - use both methods
        # Calculate method 1 wind
        if abs(angle1 - angle2) > 180:
            if angle1 < angle2:
                angle1 += 360
            else:
                angle2 += 360
                
        avg_heading = (angle1 + angle2) / 2
        if avg_heading >= 360:
            avg_heading -= 360
            
        method1_wind = (avg_heading + 90) % 360
        
        # Blend methods with preference for method 2
        weight_method1 = 0.2
        weight_method2 = 0.8
        
        if abs(method1_wind - method2_wind) > 180:
            if method1_wind < method2_wind:
                method1_wind += 360
            else:
                method2_wind += 360
                
        estimated_wind = (method1_wind * weight_method1 + method2_wind * weight_method2) / (weight_method1 + weight_method2)
        if estimated_wind >= 360:
            estimated_wind -= 360
    else:
        # Poor opposite angles - rely on method 2
        estimated_wind = method2_wind
    
    return estimated_wind