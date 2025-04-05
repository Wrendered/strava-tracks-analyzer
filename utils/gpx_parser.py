import gpxpy
import pandas as pd
import os

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

def load_gpx_from_path(file_path):
    """Load a GPX file from disk path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"GPX file not found: {file_path}")
        
    with open(file_path, 'r') as f:
        return load_gpx_file(f)
        
def get_sample_data_paths():
    """Get paths to all sample GPX files in the data directory."""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(current_dir, 'data')
    
    sample_files = []
    for file in os.listdir(data_dir):
        if file.endswith('.gpx'):
            sample_files.append(os.path.join(data_dir, file))
            
    return sample_files