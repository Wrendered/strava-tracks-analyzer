# Improved Wind and VMG Calculation Algorithm

## Current Implementation Analysis

### Wind Direction Estimation

The current wind direction estimation has these limitations:

1. **No distance weighting**: Segments are currently filtered by minimum distance, but once they pass this threshold, all segments are treated equally regardless of length.

2. **Selection bias**: The algorithm selects the "best" angles based primarily on closeness to wind and secondarily on speed, but doesn't consider segment quality (length/duration).

3. **Simple clustering**: Takes up to 5 segments in a 15° range of the best angle, without weighting them by distance or quality.

4. **Equal port/starboard handling**: The algorithm aims to balance port and starboard tacks, but doesn't account for one tack having more reliable/longer segments than the other.

### VMG Calculation

The current VMG calculation has these issues:

1. **Limited segment selection**: The `VMG upwind-ish` calculation now uses segments within 20° of best upwind angle, which is better, but still has issues.

2. **Insufficient weighting**: While we weight segments by distance when averaging VMG, we don't weight by distance when finding the best upwind angle.

3. **Outlier susceptibility**: Very short segments can still dominate the calculation.

## Proposed Improvements

### 1. Improve Wind Direction Estimation

```python
def estimate_balanced_wind_direction_with_distance_weighting(
    stretches: pd.DataFrame, 
    user_wind_direction: float, 
    suspicious_angle_threshold: float = 20,
    min_segment_distance: float = 50  # Minimum segment distance to consider (meters)
):
    """Enhanced wind direction estimation with distance weighting."""
    
    # Basic validation and filtering similar to current algorithm
    
    # Step 1: Create a weighted scoring system for segments
    stretches_copy = stretches.copy()
    stretches_copy['quality_score'] = calculate_segment_quality_score(stretches_copy)
    
    # Step 2: Split by tack
    port_tack = stretches_copy[stretches_copy['tack'] == 'Port']
    starboard_tack = stretches_copy[stretches_copy['tack'] == 'Starboard']
    
    # Step 3: Calculate weighted average angles for each tack
    port_best_angle = None
    if len(port_tack) > 0:
        # Filter by minimum distance
        port_tack = port_tack[port_tack['distance'] >= min_segment_distance]
        
        if len(port_tack) > 0:
            # Weight by quality score and distance
            port_angles = port_tack['angle_to_wind'].values
            port_weights = port_tack['distance'].values * port_tack['quality_score'].values
            
            # Calculate weighted average
            port_best_angle = np.average(port_angles, weights=port_weights)
            
            # Calculate total distance of port tack segments for balanced weighting
            port_total_distance = port_tack['distance'].sum()
    
    # Similar for starboard tack...
    
    # Step 4: Calculate balanced wind direction, weighted by total distance of each tack
    if port_best_angle is not None and starboard_best_angle is not None:
        # Weight the adjustment by relative distance of each tack
        total_distance = port_total_distance + starboard_total_distance
        port_weight = port_total_distance / total_distance
        starboard_weight = starboard_total_distance / total_distance
        
        # Calculate weighted average angle
        weighted_avg_angle = (port_best_angle * port_weight + starboard_best_angle * starboard_weight)
        
        # Calculate port/starboard imbalance
        angle_difference = starboard_best_angle - port_best_angle
        
        # Apply weighted adjustment to current wind direction
        wind_adjustment = angle_difference / 2.0  # Still use 50/50 balance as the goal
        adjusted_wind = (user_wind_direction - wind_adjustment) % 360
        
        return adjusted_wind
    
    # Fallback cases similar to current algorithm...
```

**Key improvements:**
- Add minimum segment distance filtering
- Weight segments by both distance and quality score
- Calculate weighted average for each tack
- Consider relative distances when balancing tacks

### 2. Enhance VMG Calculation

```python
def calculate_vmg_upwind(
    upwind_segments: pd.DataFrame,
    angle_range: float = 20,  # Range around best angle to include
    min_segment_distance: float = 50  # Minimum segment distance (meters)
):
    """Calculate improved VMG upwind with distance weighting."""
    upwind_vmg = None
    
    if not upwind_segments.empty:
        # Filter by minimum distance
        filtered_upwind = upwind_segments[upwind_segments['distance'] >= min_segment_distance]
        
        if not filtered_upwind.empty:
            # Step 1: Find best upwind angle weighted by distance
            # Weight by distance when finding best angle (not just by pure angle)
            angle_weights = filtered_upwind['distance'].values
            weighted_angles = filtered_upwind['angle_to_wind'].values
            
            # Find the weighted minimum angle (closest to wind weighted by distance)
            from scipy import stats
            weighted_best_angle = stats.percentile(weighted_angles, 25, weights=angle_weights)
            
            # Step 2: Filter to segments within range of best angle
            max_angle_threshold = min(weighted_best_angle + angle_range, 90)
            angle_filtered = filtered_upwind[filtered_upwind['angle_to_wind'] <= max_angle_threshold]
            
            if not angle_filtered.empty:
                # Step 3: Calculate VMG for each segment
                angle_filtered['vmg'] = angle_filtered.apply(
                    lambda row: row['speed'] * math.cos(math.radians(row['angle_to_wind'])), axis=1
                )
                
                # Step 4: Weight by distance
                vmg_values = angle_filtered['vmg'].values
                distance_weights = angle_filtered['distance'].values
                
                # Calculate weighted average VMG
                upwind_vmg = np.average(vmg_values, weights=distance_weights)
    
    return upwind_vmg
```

**Key improvements:**
- Minimum distance filtering for segments
- Weight by distance when finding best angle (not just by pure angle)
- Use 25th percentile of weighted angles instead of pure minimum
- Maintain distance weighting for final VMG calculation

### 3. Helper Functions

```python
def calculate_segment_quality_score(segments: pd.DataFrame):
    """Calculate a quality score for each segment based on multiple factors."""
    # Copy to avoid SettingWithCopyWarning
    segments_copy = segments.copy()
    
    # Normalize distance to 0-1 range
    max_distance = segments_copy['distance'].max()
    normalized_distance = segments_copy['distance'] / max_distance if max_distance > 0 else 0
    
    # Normalize speed to 0-1 range if available
    if 'speed' in segments_copy.columns:
        max_speed = segments_copy['speed'].max()
        normalized_speed = segments_copy['speed'] / max_speed if max_speed > 0 else 0
        # Speed contributes 30% to quality score
        speed_factor = 0.3 * normalized_speed
    else:
        speed_factor = 0
    
    # Duration factor if available
    if 'duration' in segments_copy.columns:
        max_duration = segments_copy['duration'].max()
        normalized_duration = segments_copy['duration'] / max_duration if max_duration > 0 else 0
        # Duration contributes 20% to quality score
        duration_factor = 0.2 * normalized_duration
    else:
        duration_factor = 0
    
    # Distance is the primary factor (50%)
    distance_factor = 0.5 * normalized_distance
    
    # Calculate final quality score (0-1 range)
    quality_score = distance_factor + speed_factor + duration_factor
    
    return quality_score
```

## Implementation Strategy

### Phase 1: Integrate Distance Weighting in VMG Calculation

1. Update the VMG upwind calculation in both UI (analysis.py) and export (gear_item.py)
2. Add minimum segment distance filtering as a parameter
3. Implement weighted best angle finding
4. Test with various segment distributions

### Phase 2: Enhance Wind Direction Estimation

1. Create a new version of the wind direction estimation algorithm with distance weighting
2. Add quality score calculation for segments
3. Modify the wind balance mechanism to consider relative distances
4. Implement comprehensive logging for debugging
5. Add fallback to original algorithm if new version fails

### Phase 3: User Interface Updates

1. Add optional settings for minimum segment distance
2. Update tooltips and documentation to explain the improved algorithm
3. Add visual indicators for segment quality in the map display
4. Provide feedback on which segments were used for calculations

## Expected Benefits

1. **More accurate wind direction**: Wind direction will be less influenced by very short segments
2. **More reliable VMG calculation**: Upwind performance metrics will better reflect actual sailing ability
3. **Better handling of mixed data**: Sessions with a mix of short and long tacks will be analyzed more fairly
4. **Improved user experience**: More stable and predictable results across different track types