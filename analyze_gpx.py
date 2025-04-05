#!/usr/bin/env python
"""
Command-line script to analyze GPX files from wingfoil sessions.
"""
import argparse
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

from utils.gpx_parser import load_gpx_from_path, get_sample_data_paths
from utils.calculations import calculate_track_metrics
from utils.analysis import find_consistent_angle_stretches, analyze_wind_angles, estimate_wind_direction
from utils.visualization import plot_polar_diagram, plot_bearing_distribution

def analyze_file(file_path, wind_direction=None, angle_tolerance=10, 
                min_duration=10, min_distance=50, min_speed=10.0, visualize=False,
                use_simple_wind_method=True):
    """Analyze a single GPX file."""
    print(f"Analyzing file: {file_path}")
    
    # Convert knots to m/s
    min_speed_ms = min_speed * 0.514444
    
    # Load GPX data
    try:
        gpx_data = load_gpx_from_path(file_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    if gpx_data.empty:
        print("No data found in GPX file.")
        return
    
    # Calculate basic metrics
    metrics = calculate_track_metrics(gpx_data)
    
    print("\nTrack Summary:")
    print(f"Date: {metrics['date']}")
    print(f"Duration: {metrics['duration']}")
    print(f"Distance: {metrics['distance']:.2f} km")
    print(f"Average Speed: {metrics['avg_speed']:.2f} knots")
    
    # Find consistent angle stretches
    stretches = find_consistent_angle_stretches(
        gpx_data, angle_tolerance, min_duration, min_distance
    )
    
    if stretches.empty:
        print("\nNo consistent angle segments found. Try adjusting parameters.")
        return
    
    # Filter by minimum speed
    stretches = stretches[stretches['speed'] >= min_speed_ms]
    
    if stretches.empty:
        print("\nNo segments meet minimum speed criteria.")
        return
    
    # Try to estimate wind direction if not provided
    if wind_direction is None:
        # Use appropriate method for wind direction estimation
        estimated_wind = estimate_wind_direction(stretches, use_simple_method=use_simple_wind_method)
        if estimated_wind is not None:
            print(f"\nEstimated wind direction: {estimated_wind:.1f}° (using {('simple' if use_simple_wind_method else 'complex')} method)")
            wind_direction = estimated_wind
        else:
            print("\nCould not estimate wind direction. Please provide one.")
            return
    
    # Calculate angles relative to wind
    stretches = analyze_wind_angles(stretches, wind_direction)
    
    # Print analysis results
    print(f"\nAnalysis Results (Wind Direction: {wind_direction}°)")
    print(f"Found {len(stretches)} consistent segments")
    
    # Upwind analysis
    upwind = stretches[stretches['angle_to_wind'] < 90]
    downwind = stretches[stretches['angle_to_wind'] >= 90]
    
    if not upwind.empty:
        print("\nUpwind Performance:")
        port = upwind[upwind['tack'] == 'Port']
        starboard = upwind[upwind['tack'] == 'Starboard']
        
        if not port.empty:
            best_port = port.loc[port['angle_to_wind'].idxmin()]
            print(f"  Best Port Upwind: {best_port['angle_to_wind']:.1f}° @ {best_port['speed']:.1f} knots")
        
        if not starboard.empty:
            best_stbd = starboard.loc[starboard['angle_to_wind'].idxmin()]
            print(f"  Best Starboard Upwind: {best_stbd['angle_to_wind']:.1f}° @ {best_stbd['speed']:.1f} knots")
    
    if not downwind.empty:
        print("\nDownwind Performance:")
        port = downwind[downwind['tack'] == 'Port']
        starboard = downwind[downwind['tack'] == 'Starboard']
        
        if not port.empty:
            best_port = port.loc[port['angle_to_wind'].idxmax()]
            print(f"  Best Port Downwind: {best_port['angle_to_wind']:.1f}° @ {best_port['speed']:.1f} knots")
        
        if not starboard.empty:
            best_stbd = starboard.loc[starboard['angle_to_wind'].idxmax()]
            print(f"  Best Starboard Downwind: {best_stbd['angle_to_wind']:.1f}° @ {best_stbd['speed']:.1f} knots")
    
    # Save data if requested
    print(f"\nFull data for {len(stretches)} segments:")
    print(stretches[['sailing_type', 'bearing', 'angle_to_wind', 'distance', 'speed', 'duration']].to_string(index=False))
    
    # Generate visualizations if requested
    if visualize:
        # Create polar diagram
        polar_fig = plot_polar_diagram(stretches, wind_direction)
        
        # Create bearing distribution
        bearing_fig = plot_bearing_distribution(stretches, wind_direction)
        
        # Display plots
        plt.figure(polar_fig.number)
        plt.show()
        
        plt.figure(bearing_fig.number)
        plt.show()
    
    return stretches

def main():
    parser = argparse.ArgumentParser(description="Analyze GPX files from wingfoil sessions")
    parser.add_argument("file", nargs="?", help="Path to the GPX file to analyze")
    parser.add_argument("--wind", type=float, help="Wind direction in degrees")
    parser.add_argument("--tolerance", type=float, default=10, help="Angle tolerance in degrees")
    parser.add_argument("--min-duration", type=float, default=10, help="Minimum segment duration in seconds")
    parser.add_argument("--min-distance", type=float, default=50, help="Minimum segment distance in meters")
    parser.add_argument("--min-speed", type=float, default=10.0, help="Minimum segment speed in knots")
    parser.add_argument("--list-samples", action="store_true", help="List available sample files")
    parser.add_argument("--sample", type=int, help="Use a sample file (specify index)")
    parser.add_argument("--visualize", "-v", action="store_true", help="Show visualization plots")
    parser.add_argument("--complex-wind", action="store_true", 
                       help="Use complex wind estimation method (better for synthetic data)")
    
    args = parser.parse_args()
    
    # Get sample files
    sample_files = get_sample_data_paths()
    
    # List sample files if requested
    if args.list_samples:
        if not sample_files:
            print("No sample files found.")
            return
        
        print("Available sample files:")
        for i, file in enumerate(sample_files):
            print(f"  [{i}] {os.path.basename(file)}")
        return
    
    # Determine which file to analyze
    if args.sample is not None:
        if not sample_files:
            print("No sample files available.")
            return
            
        if args.sample < 0 or args.sample >= len(sample_files):
            print(f"Invalid sample index. Use --list-samples to see available samples.")
            return
            
        file_path = sample_files[args.sample]
    elif args.file:
        file_path = args.file
    else:
        parser.print_help()
        return
    
    # Analyze the file
    analyze_file(
        file_path, 
        wind_direction=args.wind,
        angle_tolerance=args.tolerance,
        min_duration=args.min_duration,
        min_distance=args.min_distance,
        min_speed=args.min_speed,
        visualize=args.visualize,
        use_simple_wind_method=not args.complex_wind  # Default to simple method unless --complex-wind is specified
    )

if __name__ == "__main__":
    main()