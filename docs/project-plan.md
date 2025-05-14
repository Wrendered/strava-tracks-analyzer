# Strava Tracks Analyzer Project Plan

## Upcoming Features and Improvements

### High Priority

#### Wind Direction Calculation Improvements
- **Issue**: Currently, the wind direction calculations can be skewed by very short tacks that dominate the weighting
- **Solution**: Enhance wind direction estimation with better segment weighting
  - Weight calculations based on segment length/duration (longer segments are more reliable)
  - Consider segment consistency (discard erratic segments)
  - Implement minimum segment length requirements for wind estimation
  - Add option to filter out outlier segments based on distance from main cluster
  - Improve visualization to show which segments are used for wind estimation

#### VMG (Velocity Made Good) Enhancements
- ✅ Rename "Upwind Progress" to "VMG upwind-ish" for more accurate terminology
- ✅ Improve calculation to use distance-weighted average of all upwind segments
- ✅ Filter to only include segments within 20° of best upwind angle
- Consider implementing similar approach for downwind VMG calculation

#### UI Improvements
- ✅ Update map tooltips to emphasize angle off wind rather than absolute heading
- Add segment selection directly from the map
- Improve wind direction visualization
- Add option to show/hide specific segment types on the map

### Medium Priority

#### Analysis Enhancements
- Add jibing vs. tacking detection and statistics
- Improve detection of short tacks
- Add speed profiling by wind angle
- Analyze acceleration/deceleration patterns

#### Track Comparison
- Add ability to overlay multiple tracks
- Compare performance between different sessions
- Track progress over time

### Low Priority

#### User Experience
- Add tutorial/onboarding for first-time users
- Improve mobile experience
- Add ability to save and load analysis settings
- Add option for light/dark themes

## Technical Debt

- Fix pandas SettingWithCopyWarning issue in the VMG calculation
- Improve logging for debugging
- Refactor wind direction estimation code for better maintainability
- Add more unit tests, especially for core calculation functions

## Notes

Short tacks issue details (2025-05-13):
- Very short tacks can unduly influence wind direction calculations
- Need to weight calculations by segment length/duration
- Current angle weighting doesn't account for segment quality
- Consider implementing a clustering approach to identify consistent tack patterns
- Potential approach:
  1. Weight segments by distance or duration when calculating average angles
  2. Apply minimum thresholds for segment inclusion in wind calculations
  3. Use a confidence scoring system based on segment consistency
  4. Visualize segment weights in the UI to help users identify reliable segments