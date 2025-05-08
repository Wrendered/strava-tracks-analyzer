#!/usr/bin/env python
"""
Script to analyze wind direction estimation for a test file.
Shows detailed steps of the algorithm.
"""

import pandas as pd
import numpy as np
import logging
import sys
from utils.gpx_parser import load_gpx_from_path
from utils.simplified_wind_estimation import (
    estimate_balanced_wind_direction, 
    detect_and_remove_outliers,
    iterative_wind_estimation
)
from utils.analysis import (
    find_consistent_angle_stretches,
    analyze_wind_angles
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

def main():
    # Load the test file
    file_path = "data/test_file_270_degrees.gpx"
    user_wind_direction = 260  # Example initial wind direction
    
    logger.info(f"Loading GPX file: {file_path}")
    df, metadata = load_gpx_from_path(file_path)
    
    logger.info(f"Loaded GPX file with {len(df)} points")
    
    # Find consistent angle stretches (segments)
    angle_tolerance = 15  # degrees
    min_duration = 3  # seconds
    min_distance = 20  # meters
    
    stretches = find_consistent_angle_stretches(df, angle_tolerance, min_duration, min_distance)
    logger.info(f"Found {len(stretches)} stretches")
    
    # Print all stretches
    logger.info("\n=== ALL STRETCHES ===")
    for i, row in stretches.head(10).iterrows():
        logger.info(f"Stretch {i}: Bearing {row['bearing']:.1f}°, Distance {row['distance']:.1f}m, Speed {row['speed']:.1f} kts")
    
    # Calculate wind angles using the user wind direction
    stretches_with_angles = analyze_wind_angles(stretches.copy(), user_wind_direction)
    
    # Show tack distribution
    port_tack = stretches_with_angles[stretches_with_angles['tack'] == 'Port']
    starboard_tack = stretches_with_angles[stretches_with_angles['tack'] == 'Starboard']
    logger.info(f"Tack distribution: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
    
    # Show upwind/downwind distribution
    upwind = stretches_with_angles[stretches_with_angles['angle_to_wind'] < 90]
    downwind = stretches_with_angles[stretches_with_angles['angle_to_wind'] >= 90]
    logger.info(f"Angle distribution: Upwind={len(upwind)}, Downwind={len(downwind)}")
    
    # Show specific stretches used in the estimation
    upwind_filtered = upwind[upwind['angle_to_wind'] >= 20]  # Filter out suspicious angles
    logger.info("\n=== UPWIND SEGMENTS (angle < 90°, >= 20°) ===")
    logger.info("PORT TACK:")
    port_upwind = upwind_filtered[upwind_filtered['tack'] == 'Port'].sort_values('angle_to_wind')
    if len(port_upwind) > 0:
        for i, row in port_upwind.head(10).iterrows():
            logger.info(f"  Segment {i}: Bearing {row['bearing']:.1f}°, Angle to wind {row['angle_to_wind']:.1f}°, Speed {row['speed']:.1f} kts")
    else:
        logger.info("  No port tack upwind segments")
    
    logger.info("\nSTARBOARD TACK:")
    starboard_upwind = upwind_filtered[upwind_filtered['tack'] == 'Starboard'].sort_values('angle_to_wind')
    if len(starboard_upwind) > 0:
        for i, row in starboard_upwind.head(10).iterrows():
            logger.info(f"  Segment {i}: Bearing {row['bearing']:.1f}°, Angle to wind {row['angle_to_wind']:.1f}°, Speed {row['speed']:.1f} kts")
    else:
        logger.info("  No starboard tack upwind segments")
    
    # Step 1: Initial wind estimation with user wind direction
    logger.info("\n=== WIND DIRECTION ESTIMATION ===")
    estimated_wind = estimate_balanced_wind_direction(stretches_with_angles, user_wind_direction)
    logger.info(f"Initial wind estimate: User input {user_wind_direction}° → Estimated {estimated_wind:.1f}°")
    
    # Step 2: Detect and remove outliers with the new wind direction
    filtered_stretches, outliers_found = detect_and_remove_outliers(stretches_with_angles, estimated_wind)
    logger.info(f"Outlier detection: Found outliers = {outliers_found}, Remaining segments = {len(filtered_stretches)}")
    
    # Step 3: Re-estimate with filtered stretches
    if outliers_found:
        logger.info("Re-estimating with filtered stretches")
        filtered_with_angles = analyze_wind_angles(filtered_stretches.copy(), estimated_wind)
        final_wind = estimate_balanced_wind_direction(filtered_with_angles, estimated_wind)
        logger.info(f"Final wind estimate: {final_wind:.1f}°")
    else:
        logger.info(f"No outliers found, final wind estimate: {estimated_wind:.1f}°")
    
    # Now run the full iterative wind estimation
    logger.info("\n=== FULL ITERATIVE WIND ESTIMATION ===")
    final_wind = iterative_wind_estimation(stretches_with_angles, user_wind_direction)
    logger.info(f"Final wind from iterative estimation: {final_wind:.1f}°")
    
    # Verify the results by showing the port and starboard tack angles with the final wind
    logger.info("\n=== VERIFICATION WITH FINAL WIND ===")
    final_stretches = analyze_wind_angles(stretches.copy(), final_wind)
    
    # Calculate average angles for each tack
    port_final = final_stretches[final_stretches['tack'] == 'Port']
    starboard_final = final_stretches[final_stretches['tack'] == 'Starboard']
    
    if len(port_final) > 0:
        port_avg = port_final['angle_to_wind'].mean()
        logger.info(f"Port tack average angle: {port_avg:.1f}° (from {len(port_final)} segments)")
    
    if len(starboard_final) > 0:
        starboard_avg = starboard_final['angle_to_wind'].mean()
        logger.info(f"Starboard tack average angle: {starboard_avg:.1f}° (from {len(starboard_final)} segments)")
    
    if len(port_final) > 0 and len(starboard_final) > 0:
        logger.info(f"Combined average angle off the wind: {(port_avg + starboard_avg)/2:.1f}° (port: {port_avg:.1f}°, starboard: {starboard_avg:.1f}°)")
        logger.info(f"Difference between port and starboard: {abs(port_avg - starboard_avg):.1f}°")

if __name__ == "__main__":
    main()