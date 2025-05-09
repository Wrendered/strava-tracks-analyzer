"""
Geographic calculations utility module.

This module contains functions for calculating distances, bearings,
and other geographic utilities.
"""

import math
from typing import Tuple, Union, List
from geopy.distance import geodesic

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing between two points in degrees.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
        
    Returns:
        float: Bearing in degrees (0-359)
    """
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

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in meters.
    
    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees
        
    Returns:
        float: Distance in meters
    """
    return geodesic((lat1, lon1), (lat2, lon2)).meters

def angle_to_wind(bearing: float, wind_direction: float) -> float:
    """
    Calculate angle relative to the wind direction.
    
    This calculates the minimum angle between the bearing and the wind direction,
    representing how far off the wind we're sailing (0-180 degrees).
    
    Args:
        bearing: The direction we're traveling (0-359 degrees)
        wind_direction: The direction the wind is coming from (0-359 degrees)
    
    Returns:
        float: The angle to wind (0-180 degrees)
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
    
    return angle

def meters_per_second_to_knots(speed_ms: float) -> float:
    """
    Convert meters per second to knots.
    
    Args:
        speed_ms: Speed in meters per second
        
    Returns:
        float: Speed in knots
    """
    return speed_ms * 1.94384

def knots_to_meters_per_second(speed_knots: float) -> float:
    """
    Convert knots to meters per second.
    
    Args:
        speed_knots: Speed in knots
        
    Returns:
        float: Speed in meters per second
    """
    return speed_knots / 1.94384