"""
Track metrics calculation.

This module contains functions for calculating various metrics from track data,
such as distance, speed, and duration.
"""

from datetime import timedelta
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
from geopy.distance import geodesic
from utils.geo import meters_per_second_to_knots, knots_to_meters_per_second
from core.constants import METERS_PER_KILOMETER

def calculate_track_metrics(gpx_data: pd.DataFrame, min_speed_knots: float = 0.0) -> Dict[str, Any]:
    """
    Calculate basic metrics for the track.
    
    Args:
        gpx_data: DataFrame containing track data
        min_speed_knots: Minimum speed (in knots) to consider for average speed calculation.
                     Segments below this speed will be excluded from average speed.
                     
    Returns:
        dict: Dictionary of track metrics including:
            - date: The date of the track
            - start_time: Start time
            - end_time: End time
            - duration: Total duration as timedelta
            - total_duration_seconds: Total duration in seconds
            - distance: Total distance in kilometers
            - avg_speed: Average speed in knots
            - weighted_avg_speed: Speed weighted by duration
            - overall_avg_speed: Simple average over whole track
            - active_duration: Duration spent above min_speed
            - active_distance: Distance covered above min_speed
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
            segment_distance_m = segment_distance_km * METERS_PER_KILOMETER
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
        total_distance_km = sum(distances) / METERS_PER_KILOMETER
        metrics['distance'] = total_distance_km
        
        # Calculate average speed excluding segments below threshold
        if speeds_m_per_s:
            # Convert speeds to knots for comparison with threshold
            speeds_knots = [meters_per_second_to_knots(s) for s in speeds_m_per_s]
            
            # Filter by minimum speed
            min_speed_ms = knots_to_meters_per_second(min_speed_knots)
            active_speeds_ms = [s for s, knots in zip(speeds_m_per_s, speeds_knots) if knots >= min_speed_knots]
            active_durations = [d for d, knots in zip(segment_durations, speeds_knots) if knots >= min_speed_knots]
            
            if active_speeds_ms:
                # Calculate distance covered at speeds above threshold
                active_distance_m = sum(s * d for s, d in zip(active_speeds_ms, active_durations))
                active_time_s = sum(active_durations)
                
                # Calculate metrics
                metrics['active_duration'] = timedelta(seconds=active_time_s)
                metrics['active_distance'] = active_distance_m / METERS_PER_KILOMETER  # in km
                
                # Calculate average speed from segments above threshold
                avg_speed_ms = sum(active_speeds_ms) / len(active_speeds_ms)
                metrics['avg_speed'] = meters_per_second_to_knots(avg_speed_ms)
                
                # Calculate weighted average speed (by duration)
                if active_time_s > 0:
                    weighted_avg_ms = active_distance_m / active_time_s
                    metrics['weighted_avg_speed'] = meters_per_second_to_knots(weighted_avg_ms)
                else:
                    metrics['weighted_avg_speed'] = 0
                
                # Calculate "traditional" avg speed over whole track for comparison
                m_per_s = total_distance_km * METERS_PER_KILOMETER / metrics['total_duration_seconds'] if metrics['total_duration_seconds'] > 0 else 0
                metrics['overall_avg_speed'] = meters_per_second_to_knots(m_per_s)
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

def calculate_average_angle_from_segments(segments: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate the average angle to wind based on selected segments.
    
    This function estimates the true wind direction based on the tack patterns
    in the selected segments. It assumes the sailor is using similar angles
    on port and starboard tacks.
    
    Args:
        segments: DataFrame with sailing segments, containing at minimum:
                'bearing', 'tack', 'angle_to_wind', 'distance'
    
    Returns:
        dict: Dictionary with:
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