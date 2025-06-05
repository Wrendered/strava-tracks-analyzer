"""
Shared calculations module.

This module contains all the shared calculation functions that were previously
duplicated across multiple modules. This eliminates code duplication and 
provides a single source of truth for mathematical operations.
"""

import math
import numpy as np
import pandas as pd
from datetime import timedelta
from geopy.distance import geodesic
from typing import Dict, Any, Optional, Tuple, List
import logging

from core.constants import (
    FULL_CIRCLE_DEGREES, METERS_PER_SECOND_TO_KNOTS, KNOTS_TO_METERS_PER_SECOND,
    METERS_PER_KILOMETER, WARNING_ANGLE_TO_WIND_DEGREES, UPWIND_DOWNWIND_BOUNDARY_DEGREES,
    ANGLE_WRAP_BOUNDARY_DEGREES, QUALITY_WEIGHT_DISTANCE, QUALITY_WEIGHT_SPEED,
    QUALITY_WEIGHT_DURATION
)

logger = logging.getLogger(__name__)


# =============================================================================
# BASIC GEOMETRIC CALCULATIONS
# =============================================================================

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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
    compass_bearing = (initial_bearing + FULL_CIRCLE_DEGREES) % FULL_CIRCLE_DEGREES
    
    return compass_bearing


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters."""
    return geodesic((lat1, lon1), (lat2, lon2)).meters


def angle_to_wind(bearing: float, wind_direction: float) -> float:
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
    bearing = bearing % FULL_CIRCLE_DEGREES
    wind_direction = wind_direction % FULL_CIRCLE_DEGREES
    
    # Calculate the absolute difference
    diff = abs(bearing - wind_direction)
    
    # Take the smaller angle (0-180)
    angle = min(diff, FULL_CIRCLE_DEGREES - diff)
    
    # Log suspicious values but don't modify them - let the user decide
    if angle < WARNING_ANGLE_TO_WIND_DEGREES:
        logger.warning(f"Suspiciously small angle to wind detected: {angle}° " + 
                      f"(bearing: {bearing}°, wind: {wind_direction}°)")
    
    return angle


def calculate_angle_bisector(angle1: float, angle2: float) -> float:
    """
    Calculate the bisector of two angles, handling 0/360 degree wraparound.
    
    Args:
        angle1, angle2: Angles in degrees (0-360)
        
    Returns:
        float: Bisector angle in degrees (0-360)
    """
    # Handle angles crossing 0/360 boundary
    if abs(angle1 - angle2) > ANGLE_WRAP_BOUNDARY_DEGREES:
        if angle1 < angle2:
            angle1 += FULL_CIRCLE_DEGREES
        else:
            angle2 += FULL_CIRCLE_DEGREES
    
    bisector = (angle1 + angle2) / 2
    return bisector % FULL_CIRCLE_DEGREES


# =============================================================================
# UNIT CONVERSIONS
# =============================================================================

def meters_per_second_to_knots(speed_ms: float) -> float:
    """Convert meters per second to knots."""
    return speed_ms * METERS_PER_SECOND_TO_KNOTS


def knots_to_meters_per_second(speed_knots: float) -> float:
    """Convert knots to meters per second."""
    return speed_knots * KNOTS_TO_METERS_PER_SECOND


def meters_to_kilometers(distance_m: float) -> float:
    """Convert meters to kilometers."""
    return distance_m / METERS_PER_KILOMETER


def kilometers_to_meters(distance_km: float) -> float:
    """Convert kilometers to meters."""
    return distance_km * METERS_PER_KILOMETER


# =============================================================================
# WIND ANALYSIS
# =============================================================================

def analyze_wind_angles(segments: pd.DataFrame, wind_direction: float) -> pd.DataFrame:
    """
    Analyze sailing segments against a given wind direction.
    
    Adds columns for angle_to_wind and tack to the segments DataFrame.
    """
    # Create a copy to avoid modifying the original
    result = segments.copy()
    
    # Calculate angle to wind for each segment
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


def determine_tack(bearing: float, wind_direction: float) -> str:
    """
    Determine if a bearing represents a port or starboard tack.
    
    Args:
        bearing: Sailing bearing in degrees
        wind_direction: Wind direction in degrees
        
    Returns:
        'Port' or 'Starboard'
    """
    return 'Port' if (bearing - wind_direction) % FULL_CIRCLE_DEGREES <= ANGLE_WRAP_BOUNDARY_DEGREES else 'Starboard'


# =============================================================================
# VMG CALCULATIONS
# =============================================================================

def calculate_vmg(speed: float, angle_to_wind: float) -> float:
    """
    Calculate Velocity Made Good (VMG) toward or away from the wind.
    
    Args:
        speed: Boat speed in any unit
        angle_to_wind: Angle to wind in degrees (0-180)
        
    Returns:
        VMG in same units as speed (positive = good VMG)
    """
    return speed * abs(math.cos(math.radians(angle_to_wind)))


def calculate_vmg_upwind(segments: pd.DataFrame) -> Tuple[float, List[float]]:
    """
    Calculate upwind VMG from segments.
    
    Args:
        segments: DataFrame with 'speed', 'angle_to_wind', 'distance' columns
        
    Returns:
        tuple: (average_vmg, list_of_individual_vmgs)
    """
    if segments.empty:
        return 0.0, []
    
    # Calculate VMG for each segment
    vmg_values = []
    for _, segment in segments.iterrows():
        vmg = calculate_vmg(segment['avg_speed_knots'], segment['angle_to_wind'])
        vmg_values.append(vmg)
    
    # Calculate distance-weighted average
    if len(vmg_values) > 0:
        weights = segments['distance'].values
        avg_vmg = np.average(vmg_values, weights=weights)
        return avg_vmg, vmg_values
    
    return 0.0, []


def calculate_vmg_downwind(segments: pd.DataFrame) -> Tuple[float, List[float]]:
    """
    Calculate downwind VMG from segments.
    
    Args:
        segments: DataFrame with 'speed', 'angle_to_wind', 'distance' columns
        
    Returns:
        tuple: (average_vmg, list_of_individual_vmgs)
    """
    if segments.empty:
        return 0.0, []
    
    # For downwind, we want the component away from the wind
    # This is still cos(angle_to_wind) but we're measuring angle from wind
    vmg_values = []
    for _, segment in segments.iterrows():
        # For downwind, angle closer to 180° is better
        vmg = calculate_vmg(segment['avg_speed_knots'], segment['angle_to_wind'])
        vmg_values.append(vmg)
    
    # Calculate distance-weighted average
    if len(vmg_values) > 0:
        weights = segments['distance'].values
        avg_vmg = np.average(vmg_values, weights=weights)
        return avg_vmg, vmg_values
    
    return 0.0, []


# =============================================================================
# TRACK METRICS
# =============================================================================

def calculate_track_metrics(gpx_data: pd.DataFrame, min_speed_knots: float = 0.0) -> Dict[str, Any]:
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
            segment_distance_m = kilometers_to_meters(segment_distance_km)
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
        total_distance_km = meters_to_kilometers(sum(distances))
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
                metrics['active_distance'] = meters_to_kilometers(active_distance_m)  # in km
                
                # Calculate average speed from segments above threshold
                avg_speed_ms = sum(active_speeds_ms) / len(active_speeds_ms)
                metrics['avg_speed'] = meters_per_second_to_knots(avg_speed_ms)  # Convert to knots
                
                # Calculate weighted average speed (by duration)
                if active_time_s > 0:
                    weighted_avg_ms = active_distance_m / active_time_s
                    metrics['weighted_avg_speed'] = meters_per_second_to_knots(weighted_avg_ms)
                else:
                    metrics['weighted_avg_speed'] = 0
                
                # Calculate "traditional" avg speed over whole track for comparison
                m_per_s = kilometers_to_meters(total_distance_km) / metrics['total_duration_seconds'] if metrics['total_duration_seconds'] > 0 else 0
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


# =============================================================================
# SEGMENT QUALITY SCORING
# =============================================================================

def calculate_segment_quality_score(segments: pd.DataFrame) -> pd.Series:
    """
    Calculate quality scores for segments based on distance, speed, and duration.
    
    Args:
        segments: DataFrame with 'distance', 'avg_speed_knots', 'duration' columns
        
    Returns:
        pd.Series: Quality scores (0-1, higher is better)
    """
    if segments.empty:
        return pd.Series(dtype=float)
    
    # Normalize each metric to 0-1 range
    distance_scores = segments['distance'] / segments['distance'].max() if segments['distance'].max() > 0 else pd.Series([1.0] * len(segments))
    speed_scores = segments['avg_speed_knots'] / segments['avg_speed_knots'].max() if segments['avg_speed_knots'].max() > 0 else pd.Series([1.0] * len(segments))
    duration_scores = segments['duration'] / segments['duration'].max() if segments['duration'].max() > 0 else pd.Series([1.0] * len(segments))
    
    # Calculate weighted score
    quality_scores = (
        QUALITY_WEIGHT_DISTANCE * distance_scores +
        QUALITY_WEIGHT_SPEED * speed_scores +
        QUALITY_WEIGHT_DURATION * duration_scores
    )
    
    return quality_scores


# =============================================================================
# AVERAGE ANGLE CALCULATIONS
# =============================================================================

def calculate_average_angle_from_segments(segments: pd.DataFrame) -> Dict[str, Any]:
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