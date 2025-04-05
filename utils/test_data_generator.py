import gpxpy
import gpxpy.gpx
from datetime import datetime, timedelta
import math
import random
import os

def generate_test_gpx(output_path, duration_minutes=30, wind_direction=90):
    """
    Generate a synthetic GPX file with simulated wingfoil tracks.
    
    Parameters:
    - output_path: Where to save the GPX file
    - duration_minutes: Length of the simulated session
    - wind_direction: Direction the wind is coming FROM (degrees)
    
    Returns:
    - Path to the created file
    """
    # Create a new GPX object
    gpx = gpxpy.gpx.GPX()
    
    # Create a track
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    
    # Create a segment
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)
    
    # Start position (somewhere in San Francisco Bay)
    start_lat = 37.827
    start_lon = -122.373
    
    # Timestamps
    start_time = datetime.now().replace(microsecond=0)
    
    # Points to generate
    num_points = duration_minutes * 60  # one point per second
    
    # Sailing patterns - a series of consistent angles with transitions
    # Each pattern is (duration_seconds, bearing_degrees, speed_knots)
    sailing_patterns = [
        # Upwind port tack
        (120, (wind_direction - 45) % 360, 12),
        # Transition
        (10, (wind_direction + 90) % 360, 8),
        # Upwind starboard tack
        (120, (wind_direction + 45) % 360, 13),
        # Transition
        (10, (wind_direction + 200) % 360, 7),
        # Downwind port tack
        (120, (wind_direction - 135) % 360, 18),
        # Transition
        (10, (wind_direction - 90) % 360, 9),
        # Downwind starboard tack
        (150, (wind_direction + 135) % 360, 17),
        # Transition back to upwind
        (15, (wind_direction - 90) % 360, 8),
        # Upwind port tack
        (180, (wind_direction - 40) % 360, 13),
        # Transition
        (10, (wind_direction + 100) % 360, 7),
        # Upwind starboard tack
        (150, (wind_direction + 40) % 360, 14),
        # Long transition back to start
        (60, (wind_direction + 170) % 360, 10),
    ]
    
    current_lat = start_lat
    current_lon = start_lon
    current_time = start_time
    
    # Calculate how many points we need for the full pattern
    total_pattern_duration = sum(duration for duration, _, _ in sailing_patterns)
    
    # Generate points
    for i in range(num_points):
        # Determine which sailing pattern we're in
        pattern_time = i % total_pattern_duration
        
        # Find the current pattern
        current_pattern_idx = 0
        pattern_start_time = 0
        
        for idx, (duration, _, _) in enumerate(sailing_patterns):
            if pattern_start_time <= pattern_time < pattern_start_time + duration:
                current_pattern_idx = idx
                break
            pattern_start_time += duration
        
        # Get the current bearing and speed
        _, bearing, speed_knots = sailing_patterns[current_pattern_idx]
        
        # Add some randomness
        bearing = (bearing + random.uniform(-5, 5)) % 360
        speed = speed_knots + random.uniform(-1, 1)
        
        # Speed in meters per second
        speed_m_s = speed * 0.514444
        
        # Calculate new position
        # Distance traveled in this second in meters
        distance = speed_m_s * 1
        
        # Convert bearing to radians
        bearing_rad = math.radians(bearing)
        
        # Earth's radius in meters
        earth_radius = 6371000
        
        # Angular distance
        angular_distance = distance / earth_radius
        
        # Current lat/lon in radians
        lat1 = math.radians(current_lat)
        lon1 = math.radians(current_lon)
        
        # Calculate new position
        lat2 = math.asin(math.sin(lat1) * math.cos(angular_distance) +
                        math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing_rad))
        
        lon2 = lon1 + math.atan2(math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1),
                               math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2))
        
        # Convert back to degrees
        new_lat = math.degrees(lat2)
        new_lon = math.degrees(lon2)
        
        # Create point
        point = gpxpy.gpx.GPXTrackPoint(
            latitude=new_lat,
            longitude=new_lon,
            time=current_time
        )
        segment.points.append(point)
        
        # Update for next point
        current_lat = new_lat
        current_lon = new_lon
        current_time = current_time + timedelta(seconds=1)
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(gpx.to_xml())
    
    return output_path

def create_sample_data():
    """Create sample GPX files with different wind directions"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Create files with different wind directions
    wind_directions = [90, 180, 270, 0]  # East, South, West, North
    
    for wind in wind_directions:
        filename = f"sample_wingfoil_{wind}deg_wind.gpx"
        output_path = os.path.join(data_dir, filename)
        generate_test_gpx(output_path, duration_minutes=15, wind_direction=wind)
        print(f"Created sample GPX file: {filename}")

if __name__ == "__main__":
    create_sample_data()