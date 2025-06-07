"""
GPX file parsing and handling.

This module contains functions for loading, parsing, and processing GPX files.
"""

import os
import gpxpy
import pandas as pd
import logging
from typing import Tuple, Dict, List, Optional, Any

from core.validation import validate_file_upload, validate_gpx_dataframe, ValidationError

logger = logging.getLogger(__name__)

def load_gpx_file(gpx_file) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load and parse a GPX file into a pandas DataFrame with comprehensive validation.
    
    Args:
        gpx_file: A file-like object containing GPX data
        
    Returns:
        tuple: (DataFrame with track data, dict with metadata)
        
    Raises:
        ValidationError: If file validation or parsing fails
    """
    try:
        # Validate the uploaded file
        validate_file_upload(gpx_file)
        
        # Parse the GPX file
        gpx = gpxpy.parse(gpx_file)
        
        if not gpx.tracks:
            raise ValidationError("GPX file contains no tracks")
            
    except gpxpy.gpx.GPXException as e:
        raise ValidationError(f"Invalid GPX file format: {str(e)}") from e
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to parse GPX file: {str(e)}") from e
    
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
    
    # Create DataFrame and validate it
    df = pd.DataFrame(data)
    
    # Validate the resulting DataFrame
    validated_df = validate_gpx_dataframe(df, f"GPX file {metadata.get('name', 'unknown')}")
    
    logger.info(f"Successfully loaded GPX file with {len(validated_df)} track points")
    return validated_df, metadata

def load_gpx_from_path(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load a GPX file from disk path.
    
    Args:
        file_path: Path to the GPX file
        
    Returns:
        tuple: (DataFrame with track data, dict with metadata)
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"GPX file not found: {file_path}")
        
    with open(file_path, 'r') as f:
        data, metadata = load_gpx_file(f)
        
        # Use filename if no name was extracted
        if not metadata['name']:
            metadata['name'] = os.path.splitext(os.path.basename(file_path))[0]
            
        return data, metadata
        
def get_sample_data_paths() -> List[str]:
    """
    Get paths to all sample GPX files in the data directory.
    
    Returns:
        list: List of paths to sample GPX files
    """
    from config.settings import DATA_DIR
    
    sample_files = []
    if os.path.exists(DATA_DIR):
        for file in os.listdir(DATA_DIR):
            if file.endswith('.gpx'):
                sample_files.append(os.path.join(DATA_DIR, file))
                
    return sample_files