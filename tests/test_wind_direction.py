#!/usr/bin/env python
"""
Script to verify wind algorithm improvements on real data.

This script:
1. Takes a GPX file path as input
2. Runs both the old and improved algorithms
3. Compares the results and shows differences in port/starboard balance
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
from core.gpx import load_gpx_from_path
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles, estimate_wind_direction
from core.wind.algorithms import estimate_wind_direction_iterative

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def plot_tack_angles(stretches, wind_direction, title):
    """Create a scatter plot showing port/starboard tack angles."""
    # Analyze angles with the given wind direction
    stretches_with_angles = analyze_wind_angles(stretches.copy(), wind_direction)
    
    # Split by tack
    port_tack = stretches_with_angles[stretches_with_angles['tack'] == 'Port']
    starboard_tack = stretches_with_angles[stretches_with_angles['tack'] == 'Starboard']
    
    # Only consider upwind angles
    port_upwind = port_tack[port_tack['angle_to_wind'] < 90]
    starboard_upwind = starboard_tack[starboard_tack['angle_to_wind'] < 90]
    
    # Create scatter plot
    plt.figure(figsize=(10, 6))
    
    # Port tack
    plt.scatter(
        port_upwind['bearing'], 
        port_upwind['angle_to_wind'],
        color='red', 
        alpha=0.7, 
        label=f'Port Tack (avg={port_upwind["angle_to_wind"].mean():.1f}°)'
    )
    
    # Starboard tack
    plt.scatter(
        starboard_upwind['bearing'], 
        starboard_upwind['angle_to_wind'],
        color='blue', 
        alpha=0.7, 
        label=f'Starboard Tack (avg={starboard_upwind["angle_to_wind"].mean():.1f}°)'
    )
    
    # Add horizontal line at the suspicious angle threshold
    plt.axhline(y=20, color='gray', linestyle='--', alpha=0.5, label='Suspicious Angle Threshold (20°)')
    
    # Add title and labels
    plt.title(f"{title} - Wind Direction: {wind_direction:.1f}°")
    plt.xlabel('Bearing (degrees)')
    plt.ylabel('Angle to Wind (degrees)')
    plt.grid(alpha=0.3)
    plt.legend()
    
    # Return the figure for saving
    return plt.gcf()

def verify_algorithm(file_path, initial_wind_direction=None):
    """Run both wind algorithms and compare the results."""
    logger.info(f"Verifying algorithms on file: {file_path}")
    
    # If no initial wind direction provided, extract from filename if possible
    if initial_wind_direction is None:
        import re
        wind_match = re.search(r'(\d+)deg', file_path)
        if wind_match:
            initial_wind_direction = int(wind_match.group(1))
            logger.info(f"Extracted wind direction from filename: {initial_wind_direction}°")
        else:
            initial_wind_direction = 270  # Default to 270 degrees
            logger.info(f"Using default wind direction: {initial_wind_direction}°")
    
    # Load and process file
    df, metadata = load_gpx_from_path(file_path)
    logger.info(f"Loaded GPX file with {len(df)} points")
    
    # Extract session name from metadata or filename
    if isinstance(metadata, dict) and 'name' in metadata and metadata['name']:
        session_name = metadata['name']
    else:
        session_name = os.path.basename(file_path)
    logger.info(f"Session name: {session_name}")
    
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
    
    # Run the original algorithm (from analysis.py)
    logger.info("\n=== Running Original Algorithm ===")
    original_wind = estimate_wind_direction(stretches_with_angles.copy(), user_wind_direction=initial_wind_direction)
    
    # Run the improved algorithm
    logger.info("\n=== Running Improved Algorithm ===")
    improved_result = estimate_wind_direction_iterative(stretches_with_angles.copy(), initial_wind_direction)
    improved_wind = improved_result.direction
    
    # Analyze results
    logger.info("\n=== RESULTS COMPARISON ===")
    logger.info(f"Initial wind direction: {initial_wind_direction}°")
    logger.info(f"Original algorithm result: {original_wind:.1f}°")
    logger.info(f"Improved algorithm result: {improved_wind:.1f}°")
    logger.info(f"Difference: {abs(original_wind - improved_wind):.1f}°")
    
    # Calculate tack angles with original wind
    orig_angles = analyze_wind_angles(stretches.copy(), original_wind)
    orig_port = orig_angles[orig_angles['tack'] == 'Port']
    orig_starboard = orig_angles[orig_angles['tack'] == 'Starboard']
    
    # Calculate upwind statistics for original
    orig_port_upwind = orig_port[orig_port['angle_to_wind'] < 90]
    orig_starboard_upwind = orig_starboard[orig_starboard['angle_to_wind'] < 90]
    
    if len(orig_port_upwind) > 0 and len(orig_starboard_upwind) > 0:
        orig_port_avg = orig_port_upwind['angle_to_wind'].mean()
        orig_starboard_avg = orig_starboard_upwind['angle_to_wind'].mean()
        orig_diff = abs(orig_port_avg - orig_starboard_avg)
        
        logger.info(f"ORIGINAL: Port upwind avg: {orig_port_avg:.1f}° ({len(orig_port_upwind)} segments)")
        logger.info(f"ORIGINAL: Starboard upwind avg: {orig_starboard_avg:.1f}° ({len(orig_starboard_upwind)} segments)")
        logger.info(f"ORIGINAL: Upwind angle difference: {orig_diff:.1f}°")
    
    # Calculate tack angles with improved wind
    improved_angles = analyze_wind_angles(stretches.copy(), improved_wind)
    improved_port = improved_angles[improved_angles['tack'] == 'Port']
    improved_starboard = improved_angles[improved_angles['tack'] == 'Starboard']
    
    # Calculate upwind statistics for improved
    improved_port_upwind = improved_port[improved_port['angle_to_wind'] < 90]
    improved_starboard_upwind = improved_starboard[improved_starboard['angle_to_wind'] < 90]
    
    if len(improved_port_upwind) > 0 and len(improved_starboard_upwind) > 0:
        improved_port_avg = improved_port_upwind['angle_to_wind'].mean()
        improved_starboard_avg = improved_starboard_upwind['angle_to_wind'].mean()
        improved_diff = abs(improved_port_avg - improved_starboard_avg)
        
        logger.info(f"IMPROVED: Port upwind avg: {improved_port_avg:.1f}° ({len(improved_port_upwind)} segments)")
        logger.info(f"IMPROVED: Starboard upwind avg: {improved_starboard_avg:.1f}° ({len(improved_starboard_upwind)} segments)")
        logger.info(f"IMPROVED: Upwind angle difference: {improved_diff:.1f}°")
    
    # Create and save plots
    import os
    plot_dir = "plots"
    os.makedirs(plot_dir, exist_ok=True)
    
    # Plot original algorithm results
    fig1 = plot_tack_angles(stretches, original_wind, "Original Algorithm")
    fig1.savefig(os.path.join(plot_dir, f"{session_name}_original.png"))
    
    # Plot improved algorithm results
    fig2 = plot_tack_angles(stretches, improved_wind, "Improved Algorithm")
    fig2.savefig(os.path.join(plot_dir, f"{session_name}_improved.png"))
    
    logger.info(f"Plots saved to {plot_dir} directory")
    
    # Return comparison data
    return {
        'file_name': session_name,
        'initial_wind': initial_wind_direction,
        'original_wind': original_wind,
        'improved_wind': improved_wind,
        'difference': abs(original_wind - improved_wind),
        'original_port_avg': orig_port_avg if 'orig_port_avg' in locals() else None,
        'original_starboard_avg': orig_starboard_avg if 'orig_starboard_avg' in locals() else None,
        'original_diff': orig_diff if 'orig_diff' in locals() else None,
        'improved_port_avg': improved_port_avg if 'improved_port_avg' in locals() else None,
        'improved_starboard_avg': improved_starboard_avg if 'improved_starboard_avg' in locals() else None,
        'improved_diff': improved_diff if 'improved_diff' in locals() else None,
    }

if __name__ == "__main__":
    import os
    
    # Check if a file path was provided as an argument
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        verify_algorithm(test_file)
    else:
        # Find all GPX files in the data directory
        data_dir = "data"
        test_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.gpx')]
        
        if not test_files:
            logger.error(f"No GPX files found in {data_dir} directory")
            sys.exit(1)
        
        results = []
        
        # Test each file
        for test_file in test_files:
            try:
                result = verify_algorithm(test_file)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {test_file}: {e}")
        
        # Print summary table
        logger.info("\n========== ALGORITHM COMPARISON SUMMARY ==========")
        logger.info(f"{'File':<30} {'Initial':<8} {'Original':<10} {'Improved':<10} {'Difference':<12} {'Old Diff':<10} {'New Diff':<10}")
        logger.info("-" * 90)
        
        for result in results:
            file_name = result['file_name']
            if len(file_name) > 28:
                file_name = file_name[:25] + "..."
                
            logger.info(
                f"{file_name:<30} {result['initial_wind']:<8.1f} {result['original_wind']:<10.1f} "
                f"{result['improved_wind']:<10.1f} {result['difference']:<12.1f} "
                f"{result['original_diff']:<10.1f if result['original_diff'] else 'N/A':<10} "
                f"{result['improved_diff']:<10.1f if result['improved_diff'] else 'N/A':<10}"
            )
        
        # Calculate average improvements
        diffs = [r['improved_diff'] - r['original_diff'] for r in results if r['original_diff'] and r['improved_diff']]
        if diffs:
            avg_improvement = sum(diffs) / len(diffs)
            logger.info(f"\nAverage tack balance improvement: {avg_improvement:.1f}°")