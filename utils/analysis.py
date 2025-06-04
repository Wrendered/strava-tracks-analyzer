import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from utils.calculations import calculate_bearing, calculate_distance, angle_to_wind
from core.constants import (
    FULL_CIRCLE_DEGREES, ANGLE_WRAP_BOUNDARY_DEGREES,
    UPWIND_DOWNWIND_BOUNDARY_DEGREES, DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    METERS_PER_SECOND_TO_KNOTS, MIN_SEGMENTS_FOR_ESTIMATION,
    WIND_SEARCH_RANGE_DEGREES, WIND_SEARCH_RANGE_WIDTH_DEGREES,
    WIND_SEARCH_STEP_DEGREES, DISTANCE_QUANTILE_THRESHOLD,
    MAX_KMEANS_CLUSTERS, KMEANS_N_INIT, MIN_SCORE_FOR_USER_GUIDED,
    MIN_SCORE_FOR_MULTI_ANGLE, ANGLE_CLUSTER_RANGE_DEGREES
)

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
        angle_diff = min((df.iloc[i]['bearing'] - current_stretch['bearing']) % FULL_CIRCLE_DEGREES, 
                         (current_stretch['bearing'] - df.iloc[i]['bearing']) % FULL_CIRCLE_DEGREES)
        
        if angle_diff > angle_tolerance:
            # End of stretch
            end_idx = i - 1
            end_time = df.iloc[end_idx]['time']
            
            # Calculate metrics for this stretch
            stretch_data = df.iloc[current_stretch['start_idx']:i]
            
            if len(stretch_data) > 1:
                total_distance = stretch_data['distance_m'].sum()
                total_duration = (end_time - current_stretch['start_time']).total_seconds()
                
                # Only keep stretches that meet minimum requirements
                if total_distance >= min_distance_meters and total_duration >= min_duration_seconds:
                    # Calculate average speed for this stretch
                    avg_speed_ms = total_distance / total_duration if total_duration > 0 else 0
                    avg_speed_knots = avg_speed_ms * METERS_PER_SECOND_TO_KNOTS
                    
                    stretch = {
                        'start_time': current_stretch['start_time'],
                        'end_time': end_time,
                        'start_idx': current_stretch['start_idx'],
                        'end_idx': end_idx,
                        'bearing': current_stretch['bearing'],
                        'distance': total_distance,
                        'duration': total_duration,
                        'avg_speed_knots': avg_speed_knots,
                        'point_count': len(stretch_data)
                    }
                    stretches.append(stretch)
            
            # Start new stretch
            current_stretch = {'start_idx': i, 'start_time': df.iloc[i]['time'], 'bearing': df.iloc[i]['bearing']}
    
    # Handle the last stretch
    if current_stretch['start_idx'] < len(df) - 1:
        end_idx = len(df) - 1
        end_time = df.iloc[end_idx]['time']
        stretch_data = df.iloc[current_stretch['start_idx']:]
        
        if len(stretch_data) > 1:
            total_distance = stretch_data['distance_m'].sum()
            total_duration = (end_time - current_stretch['start_time']).total_seconds()
            
            if total_distance >= min_distance_meters and total_duration >= min_duration_seconds:
                avg_speed_ms = total_distance / total_duration if total_duration > 0 else 0
                avg_speed_knots = avg_speed_ms * METERS_PER_SECOND_TO_KNOTS
                
                stretch = {
                    'start_time': current_stretch['start_time'],
                    'end_time': end_time,
                    'start_idx': current_stretch['start_idx'],
                    'end_idx': end_idx,
                    'bearing': current_stretch['bearing'],
                    'distance': total_distance,
                    'duration': total_duration,
                    'avg_speed_knots': avg_speed_knots,
                    'point_count': len(stretch_data)
                }
                stretches.append(stretch)
    
    # Convert to DataFrame
    if stretches:
        result_df = pd.DataFrame(stretches)
        # Speed is already converted to knots in avg_speed_knots column
        return result_df
    else:
        return pd.DataFrame()

def analyze_wind_angles(stretches, wind_direction):
    """
    Analyze sailing stretches against a given wind direction.
    
    Adds columns for angle_to_wind and tack to the stretches DataFrame.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a copy to avoid modifying the original
    result = stretches.copy()
    
    # Calculate angle to wind for each stretch
    result['angle_to_wind'] = result['bearing'].apply(
        lambda bearing: angle_to_wind(bearing, wind_direction)
    )
    
    # Determine if upwind or downwind
    result['direction'] = result.apply(
        lambda row: 'Upwind' if row['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES else 'Downwind', axis=1)
    
    # Determine tack (port or starboard)
    result['tack'] = result['bearing'].apply(
        lambda x: 'Port' if (x - wind_direction) % FULL_CIRCLE_DEGREES <= ANGLE_WRAP_BOUNDARY_DEGREES else 'Starboard')
    
    return result

def estimate_wind_direction_from_upwind_tacks(stretches, suspicious_angle_threshold=DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD):
    """
    SIMPLIFIED algorithm to estimate wind direction based on upwind tacks.
    
    This method:
    1. Selects upwind segments (angle_to_wind < UPWIND_DOWNWIND_BOUNDARY_DEGREES)
    2. Filters out suspicious angles (< suspicious_angle_threshold° to wind)
    3. Gets average angles for port and starboard tacks
    4. Calculates wind direction from the bisector of the best port and starboard tracks
    
    Parameters:
    - stretches: DataFrame with sailing segments
    - suspicious_angle_threshold: Angles less than this are excluded (default: 20°)
    
    Returns:
    - Estimated wind direction or None if insufficient data
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Starting upwind tack analysis for wind direction estimation")
    
    # Filter to upwind segments only and exclude suspicious angles
    upwind = stretches[
        (stretches['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES) &
        (stretches['angle_to_wind'] >= suspicious_angle_threshold)
    ]
    
    logger.info(f"Found {len(upwind)} " + 
                f"upwind segments after removing angles < {suspicious_angle_threshold}°")
    
    if len(upwind) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning("Not enough good upwind segments for wind estimation")
        return None
    
    # Separate port and starboard tacks
    port_tacks = upwind[upwind['tack'] == 'Port']
    starboard_tacks = upwind[upwind['tack'] == 'Starboard']
    
    if len(port_tacks) == 0 or len(starboard_tacks) == 0:
        logger.warning("Need both port and starboard tacks for wind estimation")
        return None
    
    # Get distance-weighted average bearings for each tack
    port_weights = port_tacks['distance'].values
    port_bearings = port_tacks['bearing'].values
    port_best_bearing = np.average(port_bearings, weights=port_weights)
    
    starboard_weights = starboard_tacks['distance'].values
    starboard_bearings = starboard_tacks['bearing'].values
    starboard_best_bearing = np.average(starboard_bearings, weights=starboard_weights)
    
    # Calculate average angles to wind for validation
    port_best_angle = np.average(port_tacks['angle_to_wind'].values, weights=port_weights)
    starboard_best_angle = np.average(starboard_tacks['angle_to_wind'].values, weights=starboard_weights)
    
    logger.info(f"Port tack: bearing {port_best_bearing:.1f}°, angle {port_best_angle:.1f}°")
    logger.info(f"Starboard tack: bearing {starboard_best_bearing:.1f}°, angle {starboard_best_angle:.1f}°")
    
    # Check if the tacks are reasonably opposite (they should be)
    bearing_diff = abs(port_best_bearing - starboard_best_bearing)
    if bearing_diff > ANGLE_WRAP_BOUNDARY_DEGREES:
        bearing_diff = FULL_CIRCLE_DEGREES - bearing_diff
    
    if bearing_diff < UPWIND_DOWNWIND_BOUNDARY_DEGREES:
        logger.warning(f"Port and starboard bearings too similar ({bearing_diff:.1f}° apart)")
        return None
    
    current_wind = stretches.get('wind_direction', [None])[0] if 'wind_direction' in stretches.columns else None
    
    # Calculate wind direction from port tack
    if port_best_bearing is not None and port_best_angle is not None:
        # Wind = port bearing - port angle to wind
        estimated_wind = (port_best_bearing - port_best_angle) % FULL_CIRCLE_DEGREES
        logger.info(f"Estimated wind from port tack: {estimated_wind:.1f}°")
        return estimated_wind
        
    elif starboard_best_bearing is not None:
        # Wind = starboard bearing - starboard angle to wind
        estimated_wind = (starboard_best_bearing - starboard_best_angle) % FULL_CIRCLE_DEGREES
        logger.info(f"Estimated wind from starboard tack: {estimated_wind:.1f}°")
        return estimated_wind
    
    # Fallback to user-provided wind
    return current_wind

def estimate_wind_direction(stretches, use_simple_method=True, user_wind_direction=None):
    """
    Estimate wind direction based on sailing patterns.
    
    This is the main entry point for wind estimation. The complex logic has been
    refactored into separate, focused functions for better maintainability.
    
    Parameters:
    - stretches: DataFrame of consistent sailing segments
    - use_simple_method: If True, uses the refined balanced tack algorithm (recommended)
    - user_wind_direction: Optional user-provided wind direction to use as a starting point
    
    Returns:
    - Estimated wind direction in degrees, or None if estimation fails
    """
    from core.wind_estimation_orchestrator import estimate_wind_direction_orchestrated
    
    return estimate_wind_direction_orchestrated(
        segments=stretches,
        use_simple_method=use_simple_method,
        user_wind_direction=user_wind_direction
    )