#!/usr/bin/env python
"""
Test our wind direction estimation on the sample data where we know the true wind direction.
"""
import os
import pandas as pd
from core.gpx import load_gpx_from_path
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
    real_file = {"file": "3m_rocket_20kn.gpx", "true_wind": 65.5}  # Our best estimate
    
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
        gpx_data, metadata = load_gpx_from_path(file_path)
        stretches = find_consistent_angle_stretches(
            gpx_data, angle_tolerance, min_duration, min_distance
        )
        
        # Filter by minimum speed
        stretches = stretches[stretches['speed'] >= min_speed_ms]
        
        if not stretches.empty:
            # Test both methods without user input
            simple_wind = estimate_wind_direction(stretches, use_simple_method=True)
            complex_wind = estimate_wind_direction(stretches, use_simple_method=False)
            
            # Test with user-provided input (at various offsets from true wind)
            user_inputs = [
                {"offset": 0, "desc": "exact"},
                {"offset": 15, "desc": "slightly off"},
                {"offset": 30, "desc": "moderately off"},
                {"offset": 60, "desc": "significantly off"}
            ]
            
            user_guided_results = []
            for input_info in user_inputs:
                offset = input_info["offset"]
                # Create user input with offset in both directions
                user_wind_plus = (true_wind + offset) % 360
                user_wind_minus = (true_wind - offset) % 360
                
                # Test with both offsets
                guided_plus = estimate_wind_direction(stretches, use_simple_method=True, user_wind_direction=user_wind_plus)
                guided_minus = estimate_wind_direction(stretches, use_simple_method=True, user_wind_direction=user_wind_minus)
                
                # Calculate errors
                if guided_plus is not None:
                    plus_error = min(abs(guided_plus - true_wind), 360 - abs(guided_plus - true_wind))
                    user_guided_results.append({
                        "offset": f"+{offset}°",
                        "user_input": user_wind_plus,
                        "estimated": guided_plus,
                        "error": plus_error
                    })
                
                if guided_minus is not None:
                    minus_error = min(abs(guided_minus - true_wind), 360 - abs(guided_minus - true_wind))
                    user_guided_results.append({
                        "offset": f"-{offset}°",
                        "user_input": user_wind_minus,
                        "estimated": guided_minus,
                        "error": minus_error
                    })
            
            # Process standard method results
            if simple_wind is not None and complex_wind is not None:
                # Calculate error for simple method
                simple_error = min(abs(simple_wind - true_wind), 360 - abs(simple_wind - true_wind))
                
                # Calculate error for complex method
                complex_error = min(abs(complex_wind - true_wind), 360 - abs(complex_wind - true_wind))
                
                # Determine which method is better for this file
                best_wind = simple_wind if simple_error <= complex_error else complex_wind
                best_error = min(simple_error, complex_error)
                best_method = "simple" if simple_error <= complex_error else "complex"
                
                # Find best user-guided result if available
                best_guided_error = 999
                best_guided_result = None
                if user_guided_results:
                    best_guided_result = min(user_guided_results, key=lambda x: x["error"])
                    best_guided_error = best_guided_result["error"]
                
                # Determine overall best approach
                overall_best_error = min(best_error, best_guided_error if best_guided_result else 999)
                if best_guided_result and best_guided_error <= best_error:
                    overall_best_method = f"user-guided ({best_guided_result['offset']})"
                else:
                    overall_best_method = best_method
                
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
                    "user_guided_results": user_guided_results,
                    "best_guided_error": best_guided_error if best_guided_result else None,
                    "overall_best_method": overall_best_method,
                    "overall_best_error": overall_best_error,
                    "num_segments": len(stretches)
                })
                
                print(f"\nFile: {filename}")
                print(f"  True wind: {true_wind}°")
                print(f"  Simple method wind: {simple_wind:.1f}° (error: {simple_error:.1f}°)")
                print(f"  Complex method wind: {complex_wind:.1f}° (error: {complex_error:.1f}°)")
                
                # Print user-guided results
                if user_guided_results:
                    print(f"  User-guided results:")
                    for res in user_guided_results:
                        print(f"    Offset {res['offset']}: {res['estimated']:.1f}° (error: {res['error']:.1f}°)")
                    
                    if best_guided_result:
                        print(f"  Best user-guided: Offset {best_guided_result['offset']} with error {best_guided_error:.1f}°")
                
                print(f"  Overall best method: {overall_best_method} with error {overall_best_error:.1f}°")
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
        
        # Calculate average errors for all methods
        avg_simple_error = results_df['simple_error'].mean()
        avg_complex_error = results_df['complex_error'].mean()
        avg_best_error = results_df['best_error'].mean()
        avg_guided_error = results_df['best_guided_error'].dropna().mean() if 'best_guided_error' in results_df else None
        avg_overall_error = results_df['overall_best_error'].mean()
        
        # Count which method was best most often
        overall_method_counts = {}
        for method in results_df['overall_best_method']:
            if method in overall_method_counts:
                overall_method_counts[method] += 1
            else:
                overall_method_counts[method] = 1
        
        print("\nSummary:")
        print(f"  Average simple method error: {avg_simple_error:.1f}°")
        print(f"  Average complex method error: {avg_complex_error:.1f}°")
        if avg_guided_error is not None:
            print(f"  Average best user-guided error: {avg_guided_error:.1f}°")
        print(f"  Average overall best method error: {avg_overall_error:.1f}°")
        
        print("\nMethod win counts:")
        for method, count in overall_method_counts.items():
            print(f"  {method}: {count} files")
        
        # Output overall recommendations
        print("\nRecommendations:")
        if avg_guided_error is not None and avg_guided_error <= min(avg_simple_error, avg_complex_error):
            print("  1. User-guided approach gives the best results")
            print(f"     - Even with estimates off by ~30°, user input improves accuracy")
            second_best = "simple" if avg_simple_error <= avg_complex_error else "complex"
            print(f"  2. If no user input available, use the {second_best} method")
        else:
            best_auto = "simple" if avg_simple_error <= avg_complex_error else "complex"
            print(f"  1. {best_auto.capitalize()} method gives the best results")
            if avg_guided_error is not None:
                print("  2. User-guided approach can still be beneficial in some cases")
            
        # Show per-file recommendations
        print("\nPer-file recommendations:")
        for _, row in results_df.iterrows():
            print(f"  {row['file']}:")
            print(f"    Best method: {row['overall_best_method']} (error: {row['overall_best_error']:.1f}°)")
            
            # If user-guided was best, show improvement
            if 'user-guided' in row['overall_best_method']:
                best_auto_err = min(row['simple_error'], row['complex_error'])
                improvement = best_auto_err - row['overall_best_error']
                print(f"    Improvement over auto methods: {improvement:.1f}°")
            
        # For the real data file specifically
        real_data = results_df[results_df['file'] == '3m_rocket_20kn.gpx']
        if not real_data.empty:
            row = real_data.iloc[0]
            print(f"\nReal data file analysis ('3m_rocket_20kn.gpx'):")
            print(f"  Best method: {row['overall_best_method']} (error: {row['overall_best_error']:.1f}°)")
            print(f"  Simple: {row['simple_wind']:.1f}° (error: {row['simple_error']:.1f}°)")
            print(f"  Complex: {row['complex_wind']:.1f}° (error: {row['complex_error']:.1f}°)")
            
            # Print user-guided results for real data
            if 'user_guided_results' in row and row['user_guided_results']:
                print("  User-guided results (from best to worst):")
                sorted_results = sorted(row['user_guided_results'], key=lambda x: x['error'])
                for res in sorted_results[:3]:  # Show top 3
                    print(f"    Input: {res['user_input']:.1f}° ({res['offset']}): {res['estimated']:.1f}° (error: {res['error']:.1f}°)")
                    
            # Practical recommendation for real usage
            print("\nPractical recommendation for real-world usage:")
            print("  1. Always start with user-provided wind direction")
            print("  2. Use the simple method for refinement")
            print("  3. Weight upwind segments by distance for most consistent results")
            print("  4. Filter out suspicious angles (< 20°) for better accuracy")
    
    return results

if __name__ == "__main__":
    test_wind_estimation()