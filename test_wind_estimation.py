#!/usr/bin/env python
"""
Test our wind direction estimation on the sample data where we know the true wind direction.
"""
import os
import pandas as pd
from utils.gpx_parser import load_gpx_from_path
from utils.analysis import find_consistent_angle_stretches, estimate_wind_direction

def test_wind_estimation():
    """Test the wind estimation algorithm on sample files with known wind directions."""
    # Sample files with known wind directions
    sample_files = [
        {"file": "sample_wingfoil_0deg_wind.gpx", "true_wind": 0},
        {"file": "sample_wingfoil_90deg_wind.gpx", "true_wind": 90},
        {"file": "sample_wingfoil_180deg_wind.gpx", "true_wind": 180},
        {"file": "sample_wingfoil_270deg_wind.gpx", "true_wind": 270},
    ]
    
    # Real file with estimated wind direction
    real_file = {"file": "3m_pocket_rocket_20_knots.gpx", "true_wind": 65.5}  # Our best estimate
    
    # Add to the list
    all_files = sample_files + [real_file]
    
    print("Testing wind direction estimation algorithm:")
    print("------------------------------------------")
    
    # Parameters
    angle_tolerance = 10
    min_duration = 10
    min_distance = 50
    min_speed_knots = 8.0  # Lower threshold to get more segments
    min_speed_ms = min_speed_knots * 0.514444
    
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    results = []
    
    for file_info in all_files:
        filename = file_info["file"]
        true_wind = file_info["true_wind"]
        file_path = os.path.join(data_dir, filename)
        
        # Load and process the GPX file
        gpx_data = load_gpx_from_path(file_path)
        stretches = find_consistent_angle_stretches(
            gpx_data, angle_tolerance, min_duration, min_distance
        )
        
        # Filter by minimum speed
        stretches = stretches[stretches['speed'] >= min_speed_ms]
        
        if not stretches.empty:
            # Test both methods
            simple_wind = estimate_wind_direction(stretches, use_simple_method=True)
            complex_wind = estimate_wind_direction(stretches, use_simple_method=False)
            
            if simple_wind is not None and complex_wind is not None:
                # Calculate error for simple method
                simple_error = min(abs(simple_wind - true_wind), 360 - abs(simple_wind - true_wind))
                
                # Calculate error for complex method
                complex_error = min(abs(complex_wind - true_wind), 360 - abs(complex_wind - true_wind))
                
                # Determine which method is better for this file
                best_wind = simple_wind if simple_error <= complex_error else complex_wind
                best_error = min(simple_error, complex_error)
                best_method = "simple" if simple_error <= complex_error else "complex"
                
                results.append({
                    "file": filename,
                    "true_wind": true_wind,
                    "simple_wind": simple_wind,
                    "complex_wind": complex_wind,
                    "best_wind": best_wind,
                    "simple_error": simple_error,
                    "complex_error": complex_error,
                    "best_error": best_error,
                    "best_method": best_method,
                    "num_segments": len(stretches)
                })
                
                print(f"\nFile: {filename}")
                print(f"  True wind: {true_wind}°")
                print(f"  Simple method wind: {simple_wind:.1f}° (error: {simple_error:.1f}°)")
                print(f"  Complex method wind: {complex_wind:.1f}° (error: {complex_error:.1f}°)")
                print(f"  Best method: {best_method} with error {best_error:.1f}°")
                print(f"  Segments: {len(stretches)}")
            else:
                print(f"\nFile: {filename}")
                print(f"  Could not estimate wind direction (not enough segments)")
        else:
            print(f"\nFile: {filename}")
            print(f"  No valid segments found")
    
    # Summarize results
    if results:
        results_df = pd.DataFrame(results)
        
        # Calculate average errors for both methods
        avg_simple_error = results_df['simple_error'].mean()
        avg_complex_error = results_df['complex_error'].mean()
        avg_best_error = results_df['best_error'].mean()
        
        # Count which method was best most often
        simple_wins = sum(results_df['best_method'] == 'simple')
        complex_wins = sum(results_df['best_method'] == 'complex')
        
        print("\nSummary:")
        print(f"  Average simple method error: {avg_simple_error:.1f}°")
        print(f"  Average complex method error: {avg_complex_error:.1f}°")
        print(f"  Average best method error: {avg_best_error:.1f}°")
        print(f"  Simple method was best for {simple_wins} files")
        print(f"  Complex method was best for {complex_wins} files")
        
        # Output recommendations
        if avg_simple_error <= avg_complex_error:
            print("\nRecommendation: Use the simple method (use_simple_method=True)")
        else:
            print("\nRecommendation: Use the complex method (use_simple_method=False)")
            
        # Show per-file recommendations
        print("\nPer-file recommendations:")
        for _, row in results_df.iterrows():
            method = "Simple" if row['simple_error'] <= row['complex_error'] else "Complex"
            print(f"  {row['file']}: Use {method.lower()} method (error: {min(row['simple_error'], row['complex_error']):.1f}°)")
            
        # For the real data file specifically
        real_data = results_df[results_df['file'] == '3m_pocket_rocket_20_knots.gpx']
        if not real_data.empty:
            row = real_data.iloc[0]
            method = "Simple" if row['simple_error'] <= row['complex_error'] else "Complex"
            print(f"\nFor the real data file, the {method.lower()} method is better.")
            print(f"  Simple: {row['simple_wind']:.1f}° (error: {row['simple_error']:.1f}°)")
            print(f"  Complex: {row['complex_wind']:.1f}° (error: {row['complex_error']:.1f}°)")
    
    return results

if __name__ == "__main__":
    test_wind_estimation()