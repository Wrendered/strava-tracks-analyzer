# Wind Algorithm Fix and Cleanup Plan

## Problem Statement

The current wind estimation algorithm produces unbalanced port/starboard tack angles:
- Port tack: 31.6° average angle (16 segments)  
- Starboard tack: 72.7° average angle (10 segments)
- Difference: 41.1° (should be < 5° for balanced sailing)

This indicates the algorithm is not correctly finding the true wind direction.

## Root Cause Analysis

### 1. Tack Classification Issue
The fundamental issue is that tack classification (port vs starboard) is based on the initial wind estimate, but when the wind direction is adjusted, segments are NOT reclassified. This leads to:
- Segments being permanently "locked" to their initial tack assignment
- The algorithm trying to balance angles between misclassified groups
- Convergence to incorrect wind directions

### 2. Algorithm Flow Problems
Current flow:
1. Start with initial wind (270°)
2. Classify all segments as port/starboard based on 270°
3. Calculate average angles for each tack
4. Find imbalance and adjust wind
5. **BUG**: Continue using old tack classifications
6. Result: Unbalanced angles that don't reflect true sailing pattern

### 3. Additional Issues
- Overly aggressive filtering of "suspicious" angles removes valid close-hauled segments
- Weighted averaging can be skewed by a few long/fast segments
- No validation that the final result makes sailing sense

## Proposed Solution

### Phase 1: Fix the Core Algorithm (HIGH PRIORITY)

#### 1.1 Implement Proper Iterative Reclassification
```python
def estimate_wind_with_reclassification(segments, initial_wind, max_iterations=5):
    """
    Iteratively refine wind estimate with proper tack reclassification.
    """
    current_wind = initial_wind
    
    for iteration in range(max_iterations):
        # Reclassify segments with current wind estimate
        analyzed = analyze_wind_angles(segments, current_wind)
        
        # Calculate balance metrics
        port_upwind = analyzed[(analyzed['tack'] == 'Port') & 
                               (analyzed['angle_to_wind'] < 90)]
        starboard_upwind = analyzed[(analyzed['tack'] == 'Starboard') & 
                                   (analyzed['angle_to_wind'] < 90)]
        
        # Check convergence
        if is_balanced(port_upwind, starboard_upwind):
            break
            
        # Calculate new wind estimate
        new_wind = calculate_balanced_wind(port_upwind, starboard_upwind)
        
        # Check for convergence
        if abs(new_wind - current_wind) < 1.0:
            break
            
        current_wind = new_wind
    
    return current_wind
```

#### 1.2 Implement Median-Based Estimation
Replace weighted averages with robust statistics:
```python
def calculate_balanced_wind(port_segments, starboard_segments):
    """
    Find wind direction that balances port/starboard angles using median.
    """
    # Use median instead of weighted average
    port_median_angle = np.median(port_segments['angle_to_wind'])
    starboard_median_angle = np.median(starboard_segments['angle_to_wind'])
    
    # Find wind adjustment to balance
    angle_diff = port_median_angle - starboard_median_angle
    adjustment = angle_diff / 2
    
    return current_wind + adjustment
```

#### 1.3 Add Validation
Ensure results make sailing sense:
```python
def validate_wind_estimate(segments, wind_direction):
    """
    Validate that wind estimate produces realistic sailing patterns.
    """
    analyzed = analyze_wind_angles(segments, wind_direction)
    
    # Check balance
    port_angles = analyzed[analyzed['tack'] == 'Port']['angle_to_wind']
    starboard_angles = analyzed[analyzed['tack'] == 'Starboard']['angle_to_wind']
    
    # Angles should be roughly symmetric
    balance_score = abs(port_angles.median() - starboard_angles.median())
    
    # Should have reasonable upwind angles (25-50°)
    upwind_angles = analyzed[analyzed['angle_to_wind'] < 90]['angle_to_wind']
    reasonable_upwind = (upwind_angles.median() > 25) & (upwind_angles.median() < 50)
    
    return balance_score < 5 and reasonable_upwind
```

### Phase 2: Code Consolidation (MEDIUM PRIORITY)

#### 2.1 Consolidate Wind Estimation Functions
Currently we have:
- `core/wind/direction.py` - Basic methods
- `utils/simplified_wind_estimation.py` - Iterative methods
- `core/wind_estimation_methods.py` - Refactored methods
- `core/metrics_advanced.py` - Weighted estimation

Consolidate into:
- `core/wind/estimators.py` - All estimation algorithms
- `core/wind/validation.py` - Validation and scoring
- `core/wind/analysis.py` - Segment analysis functions

#### 2.2 Create Shared Calculations Module
Move duplicated calculations to `core/calculations.py`:
- VMG calculations
- Angle-to-wind calculations
- Tack analysis
- Performance metrics

#### 2.3 Standardize Data Flow
Create consistent interfaces:
```python
class WindEstimator(Protocol):
    def estimate(self, segments: pd.DataFrame, 
                initial_wind: Optional[float] = None) -> WindEstimate:
        ...

class SegmentAnalyzer(Protocol):
    def analyze(self, segments: pd.DataFrame, 
                wind_direction: float) -> pd.DataFrame:
        ...
```

### Phase 3: Testing Infrastructure (MEDIUM PRIORITY)

#### 3.1 Create Test Data Generator
```python
def generate_realistic_sailing_data(true_wind, upwind_angle=35, 
                                  noise_level=5, num_tacks=10):
    """Generate synthetic sailing data for testing."""
    # Create realistic port/starboard tacks
    # Add noise and variations
    # Return DataFrame with known ground truth
```

#### 3.2 Add Algorithm Tests
- Test convergence with various initial conditions
- Test balance with symmetric data
- Test robustness to outliers
- Test edge cases (e.g., predominantly one tack)

#### 3.3 Performance Benchmarks
- Measure convergence speed
- Compare algorithm accuracy
- Profile for bottlenecks

### Phase 4: UI/UX Improvements (LOW PRIORITY)

#### 4.1 Add Algorithm Diagnostics
- Show iteration progress
- Display balance metrics
- Highlight suspicious segments
- Show convergence graph

#### 4.2 Allow Algorithm Selection
- Let users choose estimation method
- Show confidence levels
- Allow manual override

## Implementation Order

1. **Immediate Fix** (Do First):
   - Fix the tack reclassification bug in the current algorithm
   - Add proper iteration with segment reanalysis
   - Test with current data

2. **Core Improvements** (Do Second):
   - Implement median-based estimation
   - Add validation checks
   - Improve convergence criteria

3. **Code Cleanup** (Do Third):
   - Consolidate wind estimation functions
   - Create shared calculations module
   - Remove duplicated code

4. **Testing** (Do Fourth):
   - Add unit tests for algorithms
   - Create test data generators
   - Add integration tests

5. **Polish** (Do Last):
   - UI improvements
   - Documentation
   - Performance optimization

## Success Metrics

1. **Balance**: Port/starboard angle difference < 5°
2. **Convergence**: Algorithm converges in < 5 iterations
3. **Accuracy**: Estimated wind within 5° of true wind on test data
4. **Robustness**: Handles edge cases gracefully
5. **Performance**: < 100ms for typical dataset

## Next Steps

1. Create a test to reproduce the current bug
2. Implement the reclassification fix
3. Verify the fix resolves the balance issue
4. Begin systematic refactoring following this plan