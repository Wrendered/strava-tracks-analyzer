# Enhanced Wind and VMG Algorithms PR

## Problem

The original wind direction and VMG calculation algorithms had several issues:

1. Short tacks could unduly influence calculations
2. No weighting by segment distance/duration
3. Quality of segments was not considered

## Solution

This PR implements distance-weighted algorithms that address these issues by:

1. **Segment Quality Scoring**: Each segment gets a quality score based on:
   - Distance (50% weight)
   - Speed (30% weight) 
   - Duration (20% weight)

2. **Enhanced VMG Calculation**:
   - Filters segments by minimum distance (configurable)
   - Weights segments by distance when finding the best upwind angle
   - Prioritizes longer, more reliable segments
   - Provides more accurate representation of upwind performance

3. **Improved Wind Direction Estimation**:
   - Weights angles by distance and quality score
   - Balances port and starboard tacks based on their relative distances
   - Provides more refined confidence scores

## Implementation Details

1. Created a new `metrics_advanced.py` module with:
   - `calculate_segment_quality_score`
   - `calculate_vmg_upwind` 
   - `calculate_vmg_downwind`
   - `estimate_wind_direction_weighted`

2. Added configuration parameters:
   - `DEFAULT_MIN_SEGMENT_DISTANCE` (50 meters)
   - `DEFAULT_VMG_ANGLE_RANGE` (20 degrees)

3. Updated UI to use new algorithms with better tooltips

4. Updated gear comparison export to use the improved calculations

## Testing

The new algorithms have been tested with:
- Tracks containing very short tacks
- Tracks with mixed long and short segments
- Various wind directions and angles

## Future Work

1. Add unit tests for the new algorithms
2. Create UI options to adjust minimum segment distance filter
3. Add visualization of segment quality in the map display