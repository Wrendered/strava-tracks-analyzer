import gpxpy
import pandas as pd
import os

def load_gpx_file(gpx_file):
    """Load and parse a GPX file into a pandas DataFrame.
    
    Returns:
        tuple: (DataFrame with track data, dict with metadata)
    """
    gpx = gpxpy.parse(gpx_file)
    
    # Extract metadata
    metadata = {
        'name': None,
        'description': None,
        'time': None,
        'author': None
    }
    
    # Try to get the track name from GPX data
    if gpx.tracks and gpx.tracks[0].name:
        metadata['name'] = gpx.tracks[0].name
    elif hasattr(gpx_file, 'name'):
        # Use the filename if available
        filename = os.path.basename(gpx_file.name)
        metadata['name'] = os.path.splitext(filename)[0]
    
    # Extract other metadata if available
    if gpx.description:
        metadata['description'] = gpx.description
    if gpx.time:
        metadata['time'] = gpx.time
    if gpx.author_name:
        metadata['author'] = gpx.author_name
    
    # Parse track points
    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'time': point.time,
                })
    
    return pd.DataFrame(data), metadata

def load_gpx_from_path(file_path):
    """Load a GPX file from disk path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"GPX file not found: {file_path}")
        
    with open(file_path, 'r') as f:
        data, metadata = load_gpx_file(f)
        
        # Use filename if no name was extracted
        if not metadata['name']:
            metadata['name'] = os.path.splitext(os.path.basename(file_path))[0]
            
        return data, metadata
        
def get_sample_data_paths():
    """Get paths to all sample GPX files in the data directory."""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(current_dir, 'data')
    
    sample_files = []
    for file in os.listdir(data_dir):
        if file.endswith('.gpx'):
            sample_files.append(os.path.join(data_dir, file))
            
    return sample_files