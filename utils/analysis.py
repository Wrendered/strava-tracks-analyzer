import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from utils.calculations import calculate_bearing, calculate_distance, angle_to_wind

def find_consistent_angle_stretches(df, angle_tolerance, min_duration_seconds, min_distance_meters):
    """Find stretches of consistent sailing angle."""
    if len(df) < 2:
        return pd.DataFrame()
    
    # Calculate bearing and distance for each point
    bearings = []
    distances = []
    durations = []
    
    for i in range(len(df) - 1):
        lat1, lon1 = df.iloc[i]['latitude'], df.iloc[i]['longitude']
        lat2, lon2 = df.iloc[i+1]['latitude'], df.iloc[i+1]['longitude']
        
        bearing = calculate_bearing(lat1, lon1, lat2, lon2)
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        
        bearings.append(bearing)
        distances.append(distance)
        
        if i > 0 and 'time' in df.columns and df.iloc[i]['time'] is not None and df.iloc[i-1]['time'] is not None:
            duration = (df.iloc[i]['time'] - df.iloc[i-1]['time']).total_seconds()
            durations.append(duration)
        else:
            durations.append(0)
    
    # Add one more to match length of dataframe
    bearings.append(bearings[-1] if bearings else 0)
    distances.append(distances[-1] if distances else 0)
    durations.append(durations[-1] if durations else 0)
    
    df = df.copy()
    df['bearing'] = bearings
    df['distance_m'] = distances
    df['duration_sec'] = durations
    
    # Find stretches of consistent angle
    stretches = []
    current_stretch = {'start_idx': 0, 'start_time': df.iloc[0]['time'], 'bearing': bearings[0]}
    
    for i in range(1, len(df)):
        angle_diff = min((df.iloc[i]['bearing'] - current_stretch['bearing']) % 360, 
                         (current_stretch['bearing'] - df.iloc[i]['bearing']) % 360)
        
        if angle_diff > angle_tolerance:
            # End of stretch
            end_idx = i - 1
            if end_idx > current_stretch['start_idx']:
                stretch_df = df.iloc[current_stretch['start_idx']:end_idx+1]
                total_distance = stretch_df['distance_m'].sum()
                if 'time' in df.columns and df.iloc[end_idx]['time'] is not None and current_stretch['start_time'] is not None:
                    duration = (df.iloc[end_idx]['time'] - current_stretch['start_time']).total_seconds()
                else:
                    duration = 0
                
                # Only add if meets BOTH minimum criteria
                if duration >= min_duration_seconds and total_distance >= min_distance_meters:
                    stretches.append({
                        'start_idx': current_stretch['start_idx'],
                        'end_idx': end_idx,
                        'bearing': current_stretch['bearing'],
                        'distance': total_distance,
                        'duration': duration,
                        'speed': total_distance / duration if duration > 0 else 0
                    })
            
            # Start new stretch
            current_stretch = {'start_idx': i, 'start_time': df.iloc[i]['time'], 'bearing': df.iloc[i]['bearing']}
    
    # Check if the last stretch meets criteria
    if len(df) > 0:
        if 'time' in df.columns and df.iloc[-1]['time'] is not None and current_stretch['start_time'] is not None:
            duration = (df.iloc[-1]['time'] - current_stretch['start_time']).total_seconds()
        else:
            duration = 0
        
        stretch_df = df.iloc[current_stretch['start_idx']:]
        total_distance = stretch_df['distance_m'].sum()
        
        # Only add if meets BOTH minimum criteria
        if duration >= min_duration_seconds and total_distance >= min_distance_meters:
            stretches.append({
                'start_idx': current_stretch['start_idx'],
                'end_idx': len(df) - 1,
                'bearing': current_stretch['bearing'],
                'distance': total_distance,
                'duration': duration,
                'speed': total_distance / duration if duration > 0 else 0
            })
            
    if stretches and len(stretches) > 0:
        result_df = pd.DataFrame(stretches)
        # Convert speed from m/s to knots (1 m/s = 1.94384 knots)
        result_df['speed'] = result_df['speed'] * 1.94384
        
        # Log the found stretches for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Found {len(result_df)} stretches with bearings: {result_df['bearing'].tolist()}")
        
        return result_df
    
    # Create empty DataFrame with correct columns if no stretches
    return pd.DataFrame(columns=['start_idx', 'end_idx', 'bearing', 'distance', 'duration', 'speed'])

def analyze_wind_angles(stretches, wind_direction):
    """Calculate angles relative to wind and determine tack."""
    if stretches.empty:
        return stretches
    
    # Make a copy to avoid modifying the original
    result = stretches.copy()
    
    # Add the wind direction for reference
    result['wind_direction'] = wind_direction
    
    # Calculate angles relative to wind
    result['angle_to_wind'] = result['bearing'].apply(
        lambda x: angle_to_wind(x, wind_direction))
    
    # Determine tack based on bearing relative to wind direction
    result['tack'] = result['bearing'].apply(
        lambda x: 'Port' if (x - wind_direction) % 360 <= 180 else 'Starboard')
    
    # Determine upwind vs downwind based on angle to wind
    result['upwind_downwind'] = result.apply(
        lambda row: 'Upwind' if row['angle_to_wind'] < 90 else 'Downwind', axis=1)
    
    # Create combined category for coloring and display
    result['sailing_type'] = result.apply(
        lambda row: f"{row['upwind_downwind']} {row['tack']}", axis=1)
    
    # Add debug info to help verify calculations
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Wind direction: {wind_direction}°")
    
    # Log a summary of the tacks
    port_count = sum(result['tack'] == 'Port')
    stbd_count = sum(result['tack'] == 'Starboard')
    upwind_count = sum(result['upwind_downwind'] == 'Upwind')
    downwind_count = sum(result['upwind_downwind'] == 'Downwind')
    
    logger.info(f"Tack summary: {port_count} Port, {stbd_count} Starboard")
    logger.info(f"Direction summary: {upwind_count} Upwind, {downwind_count} Downwind")
    
    return result

def estimate_wind_direction_from_upwind_tacks(stretches, suspicious_angle_threshold=20):
    """
    SIMPLIFIED algorithm to estimate wind direction based on upwind tacks.
    
    This method:
    1. Selects upwind segments (angle_to_wind < 90)
    2. Filters out suspicious angles (<20° to wind)
    3. Gets average angles for port and starboard tacks
    4. Calculates wind direction from the bisector of the best port and starboard tracks
    
    Parameters:
    - stretches: DataFrame with sailing segments
    - suspicious_angle_threshold: Angles less than this are excluded (default: 20°)
    
    Returns:
    - Estimated wind direction or None if insufficient data
    """
    # Must have required columns
    if stretches.empty or 'angle_to_wind' not in stretches.columns or 'tack' not in stretches.columns:
        return None
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Step 1: Basic filtering - get upwind segments and remove suspicious angles
    upwind = stretches[
        (stretches['angle_to_wind'] < 90) & 
        (stretches['angle_to_wind'] >= suspicious_angle_threshold)
    ].copy()
    
    logger.info(f"Using {len(upwind)}/{len(stretches[stretches['angle_to_wind'] < 90])} " +
               f"upwind segments after removing angles < {suspicious_angle_threshold}°")
    
    # Need at least 3 segments for a valid calculation
    if len(upwind) < 3:
        return None
    
    # Step 2: Split by tack - no complex filtering
    port_upwind = upwind[upwind['tack'] == 'Port']
    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
    
    # Get current wind direction (for fallback)
    current_wind = stretches['wind_direction'].iloc[0] if 'wind_direction' in stretches.columns else None
    
    # Step 3: Simple average calculations - no weighted or statistical methods
    port_best_angle = None
    port_best_bearing = None
    if len(port_upwind) > 0:
        # For port tack, take best upwind angle (smallest angle to wind)
        port_sorted = port_upwind.sort_values('angle_to_wind')
        best_port = port_sorted.iloc[0]  # Just the single best angle
        port_best_angle = best_port['angle_to_wind']
        port_best_bearing = best_port['bearing']
    
    starboard_best_angle = None
    starboard_best_bearing = None
    if len(starboard_upwind) > 0:
        # For starboard tack, same approach
        starboard_sorted = starboard_upwind.sort_values('angle_to_wind')
        best_starboard = starboard_sorted.iloc[0]  # Just the single best angle
        starboard_best_angle = best_starboard['angle_to_wind']
        starboard_best_bearing = best_starboard['bearing']
    
    # Log what we found
    logger.info(f"Best port angle: {port_best_angle}, bearing: {port_best_bearing}")
    logger.info(f"Best starboard angle: {starboard_best_angle}, bearing: {starboard_best_bearing}")
    
    # Need at least one valid tack
    if port_best_angle is None and starboard_best_angle is None:
        return None
    
    # Step 4: Calculate wind direction - simplified approach
    # If we have both tacks, use the bisector
    if port_best_bearing is not None and starboard_best_bearing is not None:
        # Handle angle wrapping around 0/360
        if abs(port_best_bearing - starboard_best_bearing) > 180:
            if port_best_bearing < starboard_best_bearing:
                port_best_bearing += 360
            else:
                starboard_best_bearing += 360
        
        # Simple 50/50 average - no weighting
        bisector = (port_best_bearing + starboard_best_bearing) / 2
        if bisector >= 360:
            bisector -= 360
            
        # The wind direction is the bisector
        estimated_wind = bisector
        logger.info(f"Estimated wind from tack bisector: {estimated_wind:.1f}°")
        return estimated_wind
    
    # If just one tack, calculate from that one
    elif port_best_bearing is not None:
        # Wind = port bearing + port angle to wind
        estimated_wind = (port_best_bearing + port_best_angle) % 360
        logger.info(f"Estimated wind from port tack: {estimated_wind:.1f}°")
        return estimated_wind
        
    elif starboard_best_bearing is not None:
        # Wind = starboard bearing - starboard angle to wind
        estimated_wind = (starboard_best_bearing - starboard_best_angle) % 360
        logger.info(f"Estimated wind from starboard tack: {estimated_wind:.1f}°")
        return estimated_wind
    
    # Fallback to user-provided wind
    return current_wind

def estimate_wind_direction(stretches, use_simple_method=True, user_wind_direction=None):
    """
    Estimate wind direction based on sailing patterns.
    
    Uses multiple methods and heuristics to estimate the wind direction:
    1. Uses user-provided wind direction as a starting point if available
    2. If use_simple_method=True, uses the advanced simplified algorithm from simplified_wind_estimation module
    3. Otherwise, uses the older algorithm with clustering and candidate testing
    
    Parameters:
    - stretches: DataFrame of consistent sailing segments
    - use_simple_method: If True, uses the refined balanced tack algorithm (recommended)
    - user_wind_direction: Optional user-provided wind direction to use as a starting point
    """
    # Import here to avoid circular imports
    import logging
    logger = logging.getLogger(__name__)
    
    # Use the simplified but more accurate algorithm if requested
    if use_simple_method and user_wind_direction is not None:
        try:
            # Import the simplified algorithm
            from utils.simplified_wind_estimation import iterative_wind_estimation
            
            # Use the iterative balanced algorithm
            estimated_wind = iterative_wind_estimation(
                stretches.copy(), 
                user_wind_direction,
                suspicious_angle_threshold=20,
                max_iterations=3
            )
            
            logger.info(f"Estimated wind using balanced tack algorithm: {estimated_wind:.1f}°")
            return estimated_wind
            
        except Exception as e:
            logger.error(f"Error in simplified wind estimation: {e}")
            # Fall back to the original algorithm
            pass
    import logging
    logger = logging.getLogger(__name__)
    
    if len(stretches) < 3:
        logger.warning("Not enough segments to estimate wind direction (need at least 3)")
        return user_wind_direction  # Return user-provided direction if available
    
    # Filter to stretches with good distance and speed
    min_distance_threshold = stretches['distance'].quantile(0.25)  # Lower threshold to include more data
    good_stretches = stretches[stretches['distance'] > min_distance_threshold]
    
    # Sort by distance to prioritize longer stretches in analysis
    good_stretches = good_stretches.sort_values('distance', ascending=False)
    
    if len(good_stretches) < 3:
        logger.warning("Not enough good quality segments to estimate wind direction")
        return user_wind_direction  # Return user-provided direction if available
    
    # Get the bearings from good stretches
    bearings = good_stretches['bearing'].values
    
    # METHOD 1: USER-GUIDED WIND ESTIMATION
    # If user has provided an approximate wind direction, use it as a starting point
    if user_wind_direction is not None:
        logger.info(f"Using user-provided wind direction ({user_wind_direction}°) as starting point")
        # Generate a range of candidate angles to test around the user-provided direction
        # Test angles within ±30° of the user's estimate with 10° steps
        range_width = 60
        step_size = 10
        num_steps = range_width // step_size + 1  # 7 steps: -30, -20, -10, 0, 10, 20, 30
        candidate_offsets = np.linspace(-range_width/2, range_width/2, num_steps)
        
        # Add the exact user wind direction to ensure we test it
        candidate_winds = [(round(user_wind_direction + offset)) % 360 for offset in candidate_offsets]
        
        # For more precision, add a few intermediate values between the 10° increments
        intermediate_offsets = [5, -5, 15, -15, 25, -25]
        for offset in intermediate_offsets:
            candidate_winds.append((round(user_wind_direction + offset)) % 360)
            
        # Remove duplicates
        candidate_winds = sorted(list(set(candidate_winds)))
        
        # Test each candidate wind direction by analyzing the resulting tack patterns
        candidate_scores = []
        for wind in candidate_winds:
            # Temporarily analyze with this wind direction
            test_result = analyze_wind_angles(good_stretches.copy(), wind)
            
            # Calculate quality score based on:
            # 1. Spread of upwind tack angles - lower is better
            # 2. Balance between port and starboard tacks - more balanced is better
            # 3. Presence of both upwind and downwind segments - more balanced is better
            
            # Get upwind segments
            upwind = test_result[test_result['angle_to_wind'] < 90]
            port_upwind = upwind[upwind['tack'] == 'Port']
            starboard_upwind = upwind[upwind['tack'] == 'Starboard']
            
            # Calculate port/starboard balance (0-1, where 1 is perfect balance)
            if len(port_upwind) > 0 and len(starboard_upwind) > 0:
                tack_balance = min(len(port_upwind), len(starboard_upwind)) / max(len(port_upwind), len(starboard_upwind))
            else:
                tack_balance = 0
                
            # Calculate upwind/downwind balance
            upwind_downwind_balance = min(len(upwind), len(test_result) - len(upwind)) / max(len(upwind), len(test_result) - len(upwind), 1)
            
            # Calculate spread of upwind angles
            if len(upwind) >= 3:
                upwind_spread = np.std(upwind['angle_to_wind'])
                # Normalize to 0-1 range (lower is better)
                normalized_spread = 1 - min(upwind_spread / 30, 1)  # Cap at 30 degrees standard deviation
            else:
                normalized_spread = 0
                
            # Calculate overall score (weighted combination)
            score = (0.5 * tack_balance +          # Weight tack balance most highly
                    0.3 * normalized_spread +      # Weight consistency of upwind angles next
                    0.2 * upwind_downwind_balance) # Weight upwind/downwind balance least
                
            candidate_scores.append((wind, score))
            logger.debug(f"Wind candidate {wind}° - Score: {score:.2f} (Tack balance: {tack_balance:.2f}, Spread: {normalized_spread:.2f})")
        
        # Select the wind direction with the highest score
        best_candidate = max(candidate_scores, key=lambda x: x[1])
        user_guided_wind = best_candidate[0]
        user_guided_score = best_candidate[1]
        
        logger.info(f"Best wind candidate from user-guided analysis: {user_guided_wind:.1f}° (score: {user_guided_score:.2f})")
        
        # Only use this result if the score is reasonable
        if user_guided_score > 0.4:  # Threshold for a reasonably good score
            return user_guided_wind
    
    # METHOD 2: BEARING CLUSTER ANALYSIS (without the 90° assumption)
    # Convert bearings to x,y coordinates on unit circle for proper clustering
    x = np.cos(np.radians(bearings))
    y = np.sin(np.radians(bearings))
    
    # Use KMeans to find clusters of bearings
    best_n = min(4, len(good_stretches) - 1)  # Cap at 4 clusters or n-1
    kmeans = KMeans(n_clusters=best_n, random_state=0, n_init=10).fit(np.column_stack([x, y]))
    
    # Get cluster centers and convert back to angles
    centers = kmeans.cluster_centers_
    center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) + 360) % 360
    
    # Count points in each cluster
    cluster_counts = [np.sum(kmeans.labels_ == i) for i in range(len(center_angles))]
    
    # Find the two most populated clusters that are most opposite
    sorted_clusters = sorted(range(len(cluster_counts)), key=lambda i: cluster_counts[i], reverse=True)
    top_clusters = sorted_clusters[:min(3, len(sorted_clusters))]
    
    # Find the most opposite pair among the top clusters
    max_diff = -1
    angle1 = angle2 = 0
    
    for i in range(len(top_clusters)):
        for j in range(i+1, len(top_clusters)):
            idx1 = top_clusters[i]
            idx2 = top_clusters[j]
            angle_i = center_angles[idx1]
            angle_j = center_angles[idx2]
            diff = abs(angle_i - angle_j)
            diff = min(diff, 360 - diff)
            if diff > max_diff:
                max_diff = diff
                angle1 = angle_i
                angle2 = angle_j
    
    # METHOD 3: TEST MULTIPLE CANDIDATE WIND ANGLES
    # Instead of assuming 90° relationship, test multiple possible angles
    candidate_winds = []
    
    # Generate candidate wind directions by testing angles off the bearing clusters
    # Test angles from 30° to 150° off the bearing (instead of fixed 90°)
    for bearing in center_angles:
        for angle_off in [30, 60, 90, 120, 150]:
            candidate_winds.append((bearing + angle_off) % 360)
            candidate_winds.append((bearing - angle_off) % 360)
    
    # Add the angle bisector of the two most opposite tacks
    if max_diff > 90:  # Only if we have reasonably opposite tacks
        # Calculate the bisector (with special handling for angles crossing 0/360)
        if abs(angle1 - angle2) > 180:
            if angle1 < angle2:
                angle1 += 360
            else:
                angle2 += 360
                
        bisector = (angle1 + angle2) / 2
        if bisector >= 360:
            bisector -= 360
            
        # Add perpendicular directions to the bisector as candidates
        candidate_winds.append(bisector)
        candidate_winds.append((bisector + 90) % 360)
        candidate_winds.append((bisector + 180) % 360)
        candidate_winds.append((bisector + 270) % 360)
    
    # If user_wind_direction is available, include it and variations
    if user_wind_direction is not None:
        candidate_winds.append(user_wind_direction)
        candidate_winds.append((user_wind_direction + 15) % 360)
        candidate_winds.append((user_wind_direction - 15) % 360)
    
    # Remove duplicates and normalize to 0-359 range
    candidate_winds = [(w % 360) for w in candidate_winds]
    candidate_winds = list(set(candidate_winds))  # Remove duplicates
    
    # Test each candidate wind by analyzing resulting segment patterns
    candidate_scores = []
    for wind in candidate_winds:
        # Temporarily analyze with this wind direction
        test_result = analyze_wind_angles(good_stretches.copy(), wind)
        
        # Calculate same quality scores as in Method 1
        upwind = test_result[test_result['angle_to_wind'] < 90]
        port_upwind = upwind[upwind['tack'] == 'Port']
        starboard_upwind = upwind[upwind['tack'] == 'Starboard']
        
        # Calculate port/starboard balance
        if len(port_upwind) > 0 and len(starboard_upwind) > 0:
            tack_balance = min(len(port_upwind), len(starboard_upwind)) / max(len(port_upwind), len(starboard_upwind))
        else:
            tack_balance = 0
            
        # Calculate upwind/downwind balance
        upwind_downwind_balance = min(len(upwind), len(test_result) - len(upwind)) / max(len(upwind), len(test_result) - len(upwind), 1)
        
        # Calculate spread of upwind angles
        if len(upwind) >= 3:
            upwind_spread = np.std(upwind['angle_to_wind'])
            normalized_spread = 1 - min(upwind_spread / 30, 1)
        else:
            normalized_spread = 0
            
        # Calculate overall score
        score = (0.5 * tack_balance + 
                0.3 * normalized_spread + 
                0.2 * upwind_downwind_balance)
            
        candidate_scores.append((wind, score))
    
    # Select the candidate with the highest score
    if candidate_scores:
        best_candidate = max(candidate_scores, key=lambda x: x[1])
        best_wind = best_candidate[0]
        best_score = best_candidate[1]
        
        logger.info(f"Best wind direction from multi-angle testing: {best_wind:.1f}° (score: {best_score:.2f})")
        
        # METHOD 4: UPWIND TACK ANALYSIS (if we have enough data)
        # Try the dedicated upwind tack analysis method as final refinement
        if best_score > 0.3:  # Only if we have a reasonable score from method 3
            # Analyze with the best wind from method 3
            refined_result = analyze_wind_angles(good_stretches.copy(), best_wind)
            
            # Try to further refine using upwind tack analysis
            refined_wind = estimate_wind_direction_from_upwind_tacks(refined_result)
            
            if refined_wind is not None:
                logger.info(f"Refined wind direction from upwind tack analysis: {refined_wind:.1f}°")
                return refined_wind
            
            # If upwind refinement fails, return the best candidate from method 3
            return best_wind
    
    # If all methods fail or have poor scores, return user direction if available
    if user_wind_direction is not None:
        logger.warning(f"Could not confidently estimate wind direction, using user-provided: {user_wind_direction}°")
        return user_wind_direction
    
    # Last resort: METHOD 5 (Legacy method as fallback)
    # Use the bisector method if we have reasonably opposite angles
    if max_diff > 90:
        # Account for angles crossing 0/360 boundary
        if abs(angle1 - angle2) > 180:
            if angle1 < angle2:
                angle1 += 360
            else:
                angle2 += 360
                
        bisector = (angle1 + angle2) / 2
        if bisector >= 360:
            bisector -= 360
            
        # Test both the bisector and perpendicular to it
        bisector_wind = bisector
        perpendicular_wind = (bisector + 90) % 360
        
        logger.info(f"Fallback method wind directions: {bisector_wind:.1f}° or {perpendicular_wind:.1f}°")
        
        # Default to perpendicular to the bisector (traditional assumption)
        return perpendicular_wind
    
    # If all else fails, return default or user value
    logger.warning("Could not estimate wind direction with confidence")
    return user_wind_direction if user_wind_direction is not None else 90