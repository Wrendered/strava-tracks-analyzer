#!/usr/bin/env python
"""
Script to test the improved wind direction estimation algorithm.
Compares the original algorithm with the new approach.
"""

import pandas as pd
import numpy as np
import logging
import sys
from utils.gpx_parser import load_gpx_from_path
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles
from utils.simplified_wind_estimation import (
    estimate_balanced_wind_direction,
    detect_and_remove_outliers,
    iterative_wind_estimation
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Get the main logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def old_iterative_wind_estimation(stretches, initial_wind_direction, suspicious_angle_threshold=20, max_iterations=3):
    """
    Original iterative wind estimation algorithm (for comparison).
    This version filters suspicious angles BEFORE each estimation.
    """
    logger = logging.getLogger("OLD_ALGO")
    current_stretches = stretches.copy()
    current_wind = initial_wind_direction
    
    logger.info(f"ORIGINAL ALGORITHM: Starting with wind {current_wind}")
    
    for iteration in range(max_iterations):
        # First, estimate wind with filtering applied BEFORE estimation
        estimated_wind = estimate_balanced_wind_direction(
            current_stretches, 
            current_wind, 
            suspicious_angle_threshold,
            filter_suspicious=True  # Original algorithm always filtered first
        )
        
        # If estimation failed, return current wind
        if estimated_wind is None:
            return current_wind
        
        # Check for suspicious angles with the new wind direction
        filtered_stretches, outliers_found = detect_and_remove_outliers(
            current_stretches, 
            estimated_wind, 
            suspicious_angle_threshold
        )
        
        # Update current values
        current_wind = estimated_wind
        logger.info(f"Iteration {iteration+1}: Wind estimate {current_wind:.1f}°")
        
        # If no outliers found or we've filtered too much, stop iterating
        if not outliers_found or len(filtered_stretches) < 3:
            break
        
        # Continue with filtered stretches
        current_stretches = filtered_stretches
        logger.info(f"Iteration {iteration+1}: Continuing with {len(current_stretches)} segments after filtering outliers")
    
    logger.info(f"ORIGINAL ALGORITHM: Final wind direction: {current_wind:.1f}°")
    return current_wind

def test_file(file_path, initial_wind_direction=None):
    """Test both algorithms on a specific GPX file."""
    logger.info(f"======== TESTING FILE: {file_path} ========")
    
    # If no initial wind direction provided, use North as default
    if initial_wind_direction is None:
        # Extract wind direction from filename if possible (e.g., 270deg_wind.gpx -> 270)
        import re
        wind_match = re.search(r'(\d+)deg', file_path)
        if wind_match:
            initial_wind_direction = int(wind_match.group(1))
            logger.info(f"Extracted wind direction from filename: {initial_wind_direction}°")
        else:
            initial_wind_direction = 0
            logger.info(f"Using default wind direction: {initial_wind_direction}°")
    
    # Load and process the file
    df, metadata = load_gpx_from_path(file_path)
    logger.info(f"Loaded GPX file with {len(df)} points")
    
    # Find consistent angle stretches
    angle_tolerance = 15  # degrees
    min_duration = 3     # seconds
    min_distance = 20    # meters
    
    stretches = find_consistent_angle_stretches(df, angle_tolerance, min_duration, min_distance)
    logger.info(f"Found {len(stretches)} consistent angle stretches")
    
    # Base analysis with initial wind direction
    stretches_with_angles = analyze_wind_angles(stretches.copy(), initial_wind_direction)
    
    # Show tack distribution
    port_tack = stretches_with_angles[stretches_with_angles['tack'] == 'Port']
    starboard_tack = stretches_with_angles[stretches_with_angles['tack'] == 'Starboard']
    logger.info(f"Tack distribution: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
    
    # Count segments with small angles to wind
    small_angle_segments = stretches_with_angles[
        (stretches_with_angles['angle_to_wind'] < 20) & 
        (stretches_with_angles['angle_to_wind'] < 90)
    ]
    logger.info(f"Found {len(small_angle_segments)} segments with suspiciously small angles to wind (< 20°)")
    
    logger.info("\n=== RUNNING ORIGINAL ALGORITHM ===")
    old_result = old_iterative_wind_estimation(
        stretches_with_angles.copy(), 
        initial_wind_direction, 
        suspicious_angle_threshold=20
    )
    
    logger.info("\n=== RUNNING IMPROVED ALGORITHM ===")
    new_result = iterative_wind_estimation(
        stretches_with_angles.copy(), 
        initial_wind_direction, 
        suspicious_angle_threshold=20
    )
    
    # Compare results
    logger.info("\n=== ALGORITHM COMPARISON ===")
    logger.info(f"Initial wind direction: {initial_wind_direction}°")
    logger.info(f"Original algorithm result: {old_result:.1f}°")
    logger.info(f"Improved algorithm result: {new_result:.1f}°")
    logger.info(f"Difference: {abs(old_result - new_result):.1f}°")
    
    # Verify the final angles with both results
    logger.info("\n=== VERIFYING ANGLES WITH ORIGINAL ALGORITHM RESULT ===")
    old_stretches = analyze_wind_angles(stretches.copy(), old_result)
    
    # Calculate average angles for each tack
    old_port = old_stretches[old_stretches['tack'] == 'Port']
    old_starboard = old_stretches[old_stretches['tack'] == 'Starboard']
    
    if len(old_port) > 0:
        old_port_avg = old_port['angle_to_wind'].mean()
        logger.info(f"ORIGINAL: Port tack average angle: {old_port_avg:.1f}° (from {len(old_port)} segments)")
    
    if len(old_starboard) > 0:
        old_starboard_avg = old_starboard['angle_to_wind'].mean()
        logger.info(f"ORIGINAL: Starboard tack average angle: {old_starboard_avg:.1f}° (from {len(old_starboard)} segments)")
    
    if len(old_port) > 0 and len(old_starboard) > 0:
        old_diff = abs(old_port_avg - old_starboard_avg)
        logger.info(f"ORIGINAL: Difference between port and starboard: {old_diff:.1f}°")
    
    logger.info("\n=== VERIFYING ANGLES WITH IMPROVED ALGORITHM RESULT ===")
    new_stretches = analyze_wind_angles(stretches.copy(), new_result)
    
    # Calculate average angles for each tack
    new_port = new_stretches[new_stretches['tack'] == 'Port']
    new_starboard = new_stretches[new_stretches['tack'] == 'Starboard']
    
    if len(new_port) > 0:
        new_port_avg = new_port['angle_to_wind'].mean()
        logger.info(f"IMPROVED: Port tack average angle: {new_port_avg:.1f}° (from {len(new_port)} segments)")
    
    if len(new_starboard) > 0:
        new_starboard_avg = new_starboard['angle_to_wind'].mean()
        logger.info(f"IMPROVED: Starboard tack average angle: {new_starboard_avg:.1f}° (from {len(new_starboard)} segments)")
    
    if len(new_port) > 0 and len(new_starboard) > 0:
        new_diff = abs(new_port_avg - new_starboard_avg)
        logger.info(f"IMPROVED: Difference between port and starboard: {new_diff:.1f}°")
    
    # Return the comparison results
    return {
        'file': file_path,
        'initial_wind': initial_wind_direction,
        'old_result': old_result,
        'new_result': new_result,
        'difference': abs(old_result - new_result),
        'old_port_avg': old_port_avg if 'old_port_avg' in locals() else None,
        'old_starboard_avg': old_starboard_avg if 'old_starboard_avg' in locals() else None,
        'old_diff': old_diff if 'old_diff' in locals() else None,
        'new_port_avg': new_port_avg if 'new_port_avg' in locals() else None,
        'new_starboard_avg': new_starboard_avg if 'new_starboard_avg' in locals() else None,
        'new_diff': new_diff if 'new_diff' in locals() else None,
    }

def main():
    # Test files with different wind directions
    test_files = [
        "data/test_file_270_degrees.gpx",  # Main test file
        "data/sample_wingfoil_270deg_wind.gpx",  # Sample 270° wind
        "data/sample_wingfoil_90deg_wind.gpx",   # Sample 90° wind
    ]
    
    results = []
    
    for file_path in test_files:
        try:
            # Test each file with a starting wind direction
            result = test_file(file_path)
            results.append(result)
        except Exception as e:
            logger.error(f"Error testing file {file_path}: {e}")
    
    # Print summary table
    logger.info("\n========== ALGORITHM COMPARISON SUMMARY ==========")
    logger.info(f"{'File':<30} {'Initial':<8} {'Original':<10} {'Improved':<10} {'Difference':<12} {'Old Diff':<10} {'New Diff':<10}")
    logger.info("-" * 90)
    
    for result in results:
        file_name = result['file'].split('/')[-1]
        logger.info(f"{file_name:<30} {result['initial_wind']:<8.1f} {result['old_result']:<10.1f} {result['new_result']:<10.1f} "
                   f"{result['difference']:<12.1f} {result['old_diff'] if result['old_diff'] else 'N/A':<10} "
                   f"{result['new_diff'] if result['new_diff'] else 'N/A':<10}")

if __name__ == "__main__":
    main()