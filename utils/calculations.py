import math
from datetime import timedelta
from geopy.distance import geodesic
import numpy as np

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

def calculate_track_metrics(gpx_data, min_speed_knots=0.0):
    """
    Calculate basic metrics for the track.
    
    Parameters:
    - gpx_data: DataFrame containing track data
    - min_speed_knots: Minimum speed (in knots) to consider for average speed calculation.
                       Segments below this speed will be excluded from average speed.
    """
    metrics = {}
    
    if 'time' in gpx_data.columns and gpx_data['time'].notna().any():
        start_time = gpx_data['time'].min()
        end_time = gpx_data['time'].max()
        duration = end_time - start_time
        
        metrics['date'] = start_time.date()
        metrics['start_time'] = start_time
        metrics['end_time'] = end_time
        metrics['duration'] = duration
        metrics['total_duration_seconds'] = duration.total_seconds()
    else:
        metrics['duration'] = timedelta(0)
        metrics['total_duration_seconds'] = 0
    
    # Calculate total distance and speed for each segment
    if len(gpx_data) > 1:
        distances = []
        speeds_m_per_s = []
        segment_durations = []
        
        for i in range(len(gpx_data) - 1):
            point1 = (gpx_data.iloc[i]['latitude'], gpx_data.iloc[i]['longitude'])
            point2 = (gpx_data.iloc[i+1]['latitude'], gpx_data.iloc[i+1]['longitude'])
            
            # Calculate distance for this segment
            segment_distance_km = geodesic(point1, point2).kilometers
            segment_distance_m = segment_distance_km * 1000
            distances.append(segment_distance_m)
            
            # Calculate duration and speed if time data available
            if 'time' in gpx_data.columns and gpx_data.iloc[i]['time'] is not None and gpx_data.iloc[i+1]['time'] is not None:
                segment_duration = (gpx_data.iloc[i+1]['time'] - gpx_data.iloc[i]['time']).total_seconds()
                segment_durations.append(segment_duration)
                
                # Calculate speed in m/s
                if segment_duration > 0:
                    speed_m_per_s = segment_distance_m / segment_duration
                    speeds_m_per_s.append(speed_m_per_s)
        
        # Total distance in kilometers
        total_distance_km = sum(distances) / 1000
        metrics['distance'] = total_distance_km
        
        # Calculate average speed excluding segments below threshold
        if speeds_m_per_s:
            # Convert speeds to knots for comparison with threshold
            speeds_knots = [s * 1.94384 for s in speeds_m_per_s]
            
            # Filter by minimum speed
            min_speed_ms = min_speed_knots / 1.94384
            active_speeds_ms = [s for s, knots in zip(speeds_m_per_s, speeds_knots) if knots >= min_speed_knots]
            active_durations = [d for d, knots in zip(segment_durations, speeds_knots) if knots >= min_speed_knots]
            
            if active_speeds_ms:
                # Calculate distance covered at speeds above threshold
                active_distance_m = sum(s * d for s, d in zip(active_speeds_ms, active_durations))
                active_time_s = sum(active_durations)
                
                # Calculate metrics
                metrics['active_duration'] = timedelta(seconds=active_time_s)
                metrics['active_distance'] = active_distance_m / 1000  # in km
                
                # Calculate average speed from segments above threshold
                avg_speed_ms = sum(active_speeds_ms) / len(active_speeds_ms)
                metrics['avg_speed'] = avg_speed_ms * 1.94384  # Convert to knots
                
                # Calculate weighted average speed (by duration)
                if active_time_s > 0:
                    weighted_avg_ms = active_distance_m / active_time_s
                    metrics['weighted_avg_speed'] = weighted_avg_ms * 1.94384
                else:
                    metrics['weighted_avg_speed'] = 0
                
                # Calculate "traditional" avg speed over whole track for comparison
                m_per_s = total_distance_km * 1000 / metrics['total_duration_seconds'] if metrics['total_duration_seconds'] > 0 else 0
                metrics['overall_avg_speed'] = m_per_s * 1.94384
            else:
                # If there are no segments above the threshold
                metrics['active_duration'] = timedelta(seconds=0)
                metrics['active_distance'] = 0
                metrics['avg_speed'] = 0
                metrics['weighted_avg_speed'] = 0
                metrics['overall_avg_speed'] = 0
        else:
            # No speed data available
            metrics['avg_speed'] = 0
            metrics['weighted_avg_speed'] = 0
            metrics['overall_avg_speed'] = 0
    else:
        # Not enough points for calculation
        metrics['distance'] = 0
        metrics['avg_speed'] = 0
        metrics['weighted_avg_speed'] = 0
        metrics['overall_avg_speed'] = 0
    
    return metrics

def meters_per_second_to_knots(speed_ms):
    """Convert meters per second to knots."""
    return speed_ms * 1.94384

def angle_to_wind(bearing, wind_direction):
    """
    Calculate angle relative to the wind direction.
    
    This calculates the minimum angle between the bearing and the wind direction,
    representing how far off the wind we're sailing (0-180 degrees).
    
    Parameters:
    - bearing: The direction we're traveling (0-359 degrees)
    - wind_direction: The direction the wind is coming from (0-359 degrees)
    
    Returns:
    - The angle to wind (0-180 degrees)
      - 0° means sailing directly INTO the wind (impossible)
      - 90° means sailing ACROSS the wind (beam reach)
      - 180° means sailing directly away from the wind (downwind)
    """
    # Ensure input values are within 0-359 range
    bearing = bearing % 360
    wind_direction = wind_direction % 360
    
    # Calculate the absolute difference
    diff = abs(bearing - wind_direction)
    
    # Take the smaller angle (0-180)
    angle = min(diff, 360 - diff)
    
    # Log suspicious values but don't modify them - let the user decide
    if angle < 15:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Suspiciously small angle to wind detected: {angle}° " + 
                      f"(bearing: {bearing}°, wind: {wind_direction}°)")
        # Note: We'll flag this for the user to review rather than silently modifying it
    
    return angle

def calculate_average_angle_from_segments(segments):
    """
    Calculate the average angle to wind based on selected segments.
    
    This function estimates the true wind direction based on the tack patterns
    in the selected segments. It assumes the sailor is using similar angles
    on port and starboard tacks.
    
    Parameters:
    - segments: DataFrame with sailing segments, containing at minimum:
                'bearing', 'tack', 'angle_to_wind', 'distance'
    
    Returns:
    - Dictionary with:
      - average_angle: the average angle off the wind across tacks
      - port_average: average angle off the wind on port tack
      - starboard_average: average angle off the wind on starboard tack
      - selected_bearings: the bearings used for calculation
      - port_count: number of port tack segments used
      - starboard_count: number of starboard tack segments used
    """
    if segments.empty:
        return {
            'average_angle': None,
            'port_average': None,
            'starboard_average': None,
            'selected_bearings': [],
            'port_count': 0,
            'starboard_count': 0
        }
    
    import numpy as np
    import logging
    logger = logging.getLogger(__name__)
    
    # Split by tack
    port_tack = segments[segments['tack'] == 'Port']
    starboard_tack = segments[segments['tack'] == 'Starboard']
    
    # Get averages for each tack (weighted by distance)
    port_average = None
    starboard_average = None
    avg_angle = None
    port_bearings = []
    starboard_bearings = []
    
    if not port_tack.empty:
        # Weight by distance
        port_weights = port_tack['distance'].values
        port_angles = port_tack['angle_to_wind'].values
        port_bearings = port_tack['bearing'].values.tolist()
        
        # Calculate weighted average
        port_average = np.average(port_angles, weights=port_weights)
        logger.info(f"Port tack average angle: {port_average:.1f}° (from {len(port_tack)} segments)")
    
    if not starboard_tack.empty:
        # Weight by distance
        starboard_weights = starboard_tack['distance'].values
        starboard_angles = starboard_tack['angle_to_wind'].values
        starboard_bearings = starboard_tack['bearing'].values.tolist()
        
        # Calculate weighted average
        starboard_average = np.average(starboard_angles, weights=starboard_weights)
        logger.info(f"Starboard tack average angle: {starboard_average:.1f}° (from {len(starboard_tack)} segments)")
    
    # If we have data from both tacks, average them
    if port_average is not None and starboard_average is not None:
        avg_angle = (port_average + starboard_average) / 2
        logger.info(f"Combined average angle off the wind: {avg_angle:.1f}° " +
                   f"(port: {port_average:.1f}°, starboard: {starboard_average:.1f}°)")
    elif port_average is not None:
        avg_angle = port_average
        logger.info(f"Using only port tack data for average angle: {avg_angle:.1f}°")
    elif starboard_average is not None:
        avg_angle = starboard_average
        logger.info(f"Using only starboard tack data for average angle: {avg_angle:.1f}°")
    
    # Combine all bearings used
    selected_bearings = port_bearings + starboard_bearings
    
    return {
        'average_angle': avg_angle,
        'port_average': port_average,
        'starboard_average': starboard_average,
        'selected_bearings': selected_bearings,
        'port_count': len(port_tack),
        'starboard_count': len(starboard_tack)
    }