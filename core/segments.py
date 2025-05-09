"""
Segment detection and analysis.

This module contains functions for detecting and analyzing consistent segments
in track data, such as upwind and downwind runs.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from utils.geo import calculate_bearing, calculate_distance, angle_to_wind, meters_per_second_to_knots

logger = logging.getLogger(__name__)

def find_consistent_angle_stretches(
    df: pd.DataFrame, 
    angle_tolerance: float, 
    min_duration_seconds: float, 
    min_distance_meters: float
) -> pd.DataFrame:
    """
    Find stretches of consistent sailing angle in track data.
    
    Args:
        df: DataFrame with track data (must contain latitude, longitude columns)
        angle_tolerance: Maximum angle variation allowed within a stretch
        min_duration_seconds: Minimum duration in seconds for a valid stretch
        min_distance_meters: Minimum distance in meters for a valid stretch
        
    Returns:
        DataFrame: Detected stretches with their properties
    """
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
        logger.info(f"Found {len(result_df)} stretches with bearings: {result_df['bearing'].tolist()}")
        
        return result_df
    
    # Create empty DataFrame with correct columns if no stretches
    return pd.DataFrame(columns=['start_idx', 'end_idx', 'bearing', 'distance', 'duration', 'speed'])

def analyze_wind_angles(stretches: pd.DataFrame, wind_direction: float) -> pd.DataFrame:
    """
    Calculate angles relative to wind and determine tack.
    
    Args:
        stretches: DataFrame with sailing segments
        wind_direction: Wind direction in degrees (0-359)
        
    Returns:
        DataFrame: Updated stretches with wind angle information
    """
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
    
    # Log a summary of the tacks
    port_count = sum(result['tack'] == 'Port')
    stbd_count = sum(result['tack'] == 'Starboard')
    upwind_count = sum(result['upwind_downwind'] == 'Upwind')
    downwind_count = sum(result['upwind_downwind'] == 'Downwind')
    
    logger.info(f"Wind direction: {wind_direction}°")
    logger.info(f"Tack summary: {port_count} Port, {stbd_count} Starboard")
    logger.info(f"Direction summary: {upwind_count} Upwind, {downwind_count} Downwind")
    
    return result