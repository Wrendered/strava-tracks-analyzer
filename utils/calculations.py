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

def calculate_track_metrics(gpx_data):
    """Calculate basic metrics for the track."""
    metrics = {}
    
    if 'time' in gpx_data.columns and gpx_data['time'].notna().any():
        start_time = gpx_data['time'].min()
        end_time = gpx_data['time'].max()
        duration = end_time - start_time
        
        metrics['date'] = start_time.date()
        metrics['start_time'] = start_time
        metrics['end_time'] = end_time
        metrics['duration'] = duration
    else:
        metrics['duration'] = timedelta(0)
    
    # Calculate total distance
    if len(gpx_data) > 1:
        distance = 0
        for i in range(len(gpx_data) - 1):
            point1 = (gpx_data.iloc[i]['latitude'], gpx_data.iloc[i]['longitude'])
            point2 = (gpx_data.iloc[i+1]['latitude'], gpx_data.iloc[i+1]['longitude'])
            distance += geodesic(point1, point2).kilometers
        
        metrics['distance'] = distance
        # Convert m/s to knots (1 m/s = 1.94384 knots)
        m_per_s = distance * 1000 / metrics['duration'].total_seconds() if metrics['duration'].total_seconds() > 0 else 0
        metrics['avg_speed'] = m_per_s * 1.94384
    else:
        metrics['distance'] = 0
        metrics['avg_speed'] = 0
    
    return metrics

def meters_per_second_to_knots(speed_ms):
    """Convert meters per second to knots."""
    return speed_ms * 1.94384

def angle_to_wind(bearing, wind_direction):
    """Calculate angle relative to the wind direction."""
    diff = abs(bearing - wind_direction)
    return min(diff, 360 - diff)