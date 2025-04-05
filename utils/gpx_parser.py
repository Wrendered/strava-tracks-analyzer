import gpxpy
import pandas as pd

def load_gpx_file(gpx_file):
    """Load and parse a GPX file into a pandas DataFrame."""
    gpx = gpxpy.parse(gpx_file)
    
    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'time': point.time,
                })
    
    return pd.DataFrame(data)