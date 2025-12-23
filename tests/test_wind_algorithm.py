#!/usr/bin/env python
"""
Script to test the wind direction estimation algorithm.
"""

import pandas as pd
import numpy as np
import logging
import sys
from core.gpx import load_gpx_from_path
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles
from core.wind.algorithms import estimate_wind_direction_iterative

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Get the main logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def test_wind_estimation_algorithm(gpx_file_path, initial_wind_direction=270):
    """Test the wind estimation algorithm on a GPX file."""
    
    logger.info(f"Testing wind estimation with file: {gpx_file_path}")
    logger.info(f"Initial wind direction: {initial_wind_direction}°")
    
    # Load GPX file
    try:
        track_data = load_gpx_from_path(gpx_file_path)
        logger.info(f"Loaded {len(track_data)} track points")
    except Exception as e:
        logger.error(f"Failed to load GPX file: {e}")
        return
    
    # Find segments
    try:
        stretches = find_consistent_angle_stretches(
            track_data, 
            angle_tolerance=15,
            min_duration_seconds=10,
            min_distance_meters=50
        )
        logger.info(f"Found {len(stretches)} segments")
    except Exception as e:
        logger.error(f"Failed to find segments: {e}")
        return
    
    if len(stretches) == 0:
        logger.warning("No segments found")
        return
    
    # Apply wind analysis
    try:
        stretches_with_angles = analyze_wind_angles(stretches, initial_wind_direction)
        logger.info("Applied initial wind analysis")
    except Exception as e:
        logger.error(f"Failed to analyze wind angles: {e}")
        return
    
    # Test the wind estimation algorithm
    logger.info("\n=== RUNNING WIND ESTIMATION ALGORITHM ===")
    try:
        result = estimate_wind_direction_iterative(
            stretches_with_angles.copy(), 
            initial_wind_direction, 
            suspicious_angle_threshold=20
        )
        estimated_wind = result.direction
        
        logger.info(f"Estimated wind direction: {estimated_wind:.1f}°")
        logger.info(f"Confidence: {result.confidence}")
        logger.info(f"Port average angle: {result.port_average_angle:.1f}°")
        logger.info(f"Starboard average angle: {result.starboard_average_angle:.1f}°")
        
        # Re-analyze with the estimated wind direction
        final_stretches = analyze_wind_angles(stretches, estimated_wind)
        
        # Calculate tack summary
        port_angles = final_stretches[
            (final_stretches['tack'] == 'Port') & 
            (final_stretches['angle_to_wind'] < 90)
        ]['angle_to_wind']
        
        starboard_angles = final_stretches[
            (final_stretches['tack'] == 'Starboard') & 
            (final_stretches['angle_to_wind'] < 90)
        ]['angle_to_wind']
        
        logger.info(f"\n=== FINAL TACK ANALYSIS ===")
        logger.info(f"Port upwind angles: {len(port_angles)} segments, avg: {port_angles.mean():.1f}°")
        logger.info(f"Starboard upwind angles: {len(starboard_angles)} segments, avg: {starboard_angles.mean():.1f}°")
        
        # Check balance
        if len(port_angles) > 0 and len(starboard_angles) > 0:
            balance_diff = abs(port_angles.mean() - starboard_angles.mean())
            logger.info(f"Tack balance difference: {balance_diff:.1f}°")
        
    except Exception as e:
        logger.error(f"Wind estimation failed: {e}")
        return


if __name__ == "__main__":
    # Test with the default GPX file
    test_wind_estimation_algorithm("data/test_file_270_degrees.gpx", 270)