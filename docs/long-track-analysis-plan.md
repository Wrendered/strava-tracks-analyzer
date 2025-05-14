# Long Track Analysis Enhancement Plan

## Overview
This plan outlines the implementation of enhanced analysis capabilities for very long tracks (3+ hours) where wind shifts can occur and the large number of tacks may skew calculations. The core enhancements include:

1. **Adaptive Parameter Scaling** - Smart adjustment of segmentation parameters to prevent over-segmentation
2. **Track Segmentation** - Time and location-based segmentation of long tracks
3. **Wind Shift Detection** - Algorithms to identify potential wind shifts during a session
4. **Advanced Outlier Filtering** - Statistical methods to identify and handle outliers
5. **Weighted Segment Scoring** - Prioritize consistent patterns over outliers
6. **Long Track Mode UI** - Toggle between short and long track analysis modes

## Implementation Plan

### Phase 0: Adaptive Parameter Scaling (Immediate Win)

#### 0.1. Segment Consolidation
- Implement `SegmentConsolidator` in `core/segments/consolidation.py`
- Detection of over-segmentation through:
  - Total segment count (scaling triggered if count > threshold)
  - Consecutive segment analysis (identifying runs of segments on same tack)
  - Per-tack segment counting (if any tack has > N segments, adjust parameters)
- Adaptive parameter adjustment:
  - Auto-increase min_distance and min_time proportionally to segment count
  - Scale formula: `new_min = base_min * log(current_segments/ideal_segments)`
  - Scale angle tolerance if necessary based on heading variance
  
#### 0.2. Automatic Parameter Optimization
- Automatically detect over-segmentation on track load 
- Implement auto-scaling of parameters when over-segmentation is detected
- Store original parameters to allow reverting to initial values
- Add subtle notification when parameters are auto-adjusted
- Include metrics showing optimization results (e.g., "Reduced segments from 80 to 15")

#### 0.3. Integration with Current UI
- Update sliders with new parameter values when auto-adjusted
- Add "Revert to Original" button to restore pre-optimization parameters
- Display optimization metrics (before/after segment counts, quality score)
- Highlight optimized parameters visually in the UI

### Phase 1: Core Infrastructure

#### 1.1. Track Segmentation Framework
- Create a `TrackSegmentationStrategy` interface with multiple implementations:
  - `TimeBasedSegmentation` - Split tracks into time windows (30-60 min)
  - `LocationBasedSegmentation` - Split tracks based on geographical regions
  - `HybridSegmentation` - Combination of time and location
- Implement segmentation logic in `core/segments/segmentation.py`
- Add configuration parameters for segmentation thresholds

#### 1.2. Wind Shift Detection
- Implement a `WindShiftDetector` class in `core/wind/shift_detector.py`
- Detection methods:
  - Heading variance analysis over time
  - VMG consistency check across segments
  - Bayesian change point detection for heading data
- Add visualization for detected wind shifts

#### 1.3. Enhanced Parameter Scaling
- Expand the `ParameterScaler` created in Phase 0 in `utils/parameter_scaling.py`
- Add additional scaling functions for:
  - Scale based on geographical coverage (e.g., track spanning multiple areas)
  - Scale based on velocity variance
  - Scale based on detected wind shifts
- Create comprehensive configuration for scaling factors

### Phase 2: Advanced Analysis

#### 2.1. Statistical Outlier Filtering
- Implement `OutlierFilter` class in `utils/outlier_detection.py` with methods:
  - Z-score filtering for speed and heading
  - IQR-based filtering for tack performance
  - Isolation Forest for multivariate outlier detection
- Add visualization of detected outliers

#### 2.2. Weighted Segment Scoring
- Create a `SegmentScorer` in `core/segments/scoring.py`
- Implement scoring based on:
  - Segment duration
  - Consistency of VMG
  - Consistency of heading
  - Wind angle consistency
- Use scores to weight segment importance in overall analysis

#### 2.3. Enhanced Data Models
- Update `Track` and `TrackSegment` classes to support:
  - Multiple wind directions per track
  - Segmentation metadata
  - Quality scores for segments
  - Confidence intervals for measurements

### Phase 3: User Interface

#### 3.1. Long Track Mode Toggle
- Add mode selector in UI (`ui/components/track_mode_selector.py`)
- Implement preset configurations for each mode
- Add visual indication of current mode

#### 3.2. Segmentation Controls
- Create UI for segmentation parameter adjustment
- Add visualization of segmentation boundaries
- Implement segment selection/filtering in UI

#### 3.3. Enhanced Visualizations
- Create multi-segment wind rose
- Add time-series visualization of wind direction changes
- Implement segment comparison views
- Create geographical visualization of track segments with wind overlay

#### 3.4. Results Presentation
- Design summary view for multi-segment analysis
- Create comparative metrics across segments
- Implement exportable segment-by-segment report

## Technical Implementation Details

### New Files
- `core/segments/consolidation.py` - For Phase 0 segment consolidation
- `utils/parameter_scaling.py` - For adaptive parameter scaling
- `core/segments/segmentation.py` - For track segmentation
- `core/wind/shift_detector.py` - For wind shift detection
- `utils/outlier_detection.py` - For outlier filtering
- `core/segments/scoring.py` - For segment scoring
- `ui/components/track_mode_selector.py` - For mode selection
- `ui/components/segment_visualization.py` - For enhanced visualization

### Modified Files
- `core/segments/__init__.py` - Export new segmentation functions
- `core/segments.py` - Add adaptive parameter adjustment
- `core/wind/estimate.py` - Integrate wind shift detection
- `core/metrics.py` - Add segment-aware metrics
- `ui/pages/analysis.py` - Add automatic parameter optimization
- `ui/components/visualization.py` - Enhanced visualizations
- `config/settings.py` - Add configuration for long tracks

### Data Models
```python
class SegmentationParams:
    min_distance: float
    min_time: float
    max_angle_tolerance: float
    quality_score: float
    
    @classmethod
    def calculate_optimal(cls, track: pd.DataFrame, ideal_segment_count: int = 20) -> 'SegmentationParams':
        """Calculate optimal segmentation parameters based on track characteristics"""
        pass

class TrackSegment:
    start_time: datetime
    end_time: datetime
    location_bounds: Tuple[float, float, float, float]  # min_lat, min_lon, max_lat, max_lon
    points: pd.DataFrame
    metrics: Dict[str, float]
    wind_direction: float
    confidence_score: float
    
class Track:
    segments: List[TrackSegment]
    primary_wind_direction: float
    wind_shift_points: List[Tuple[datetime, float]]  # time and new direction
    segmentation_method: str
    mode: str  # 'short' or 'long'
    optimal_segmentation_params: SegmentationParams
    original_segmentation_params: SegmentationParams  # Store original params for reverting
```

### Adaptive Parameter Scaling Implementation
```python
def analyze_segmentation_quality(stretches: pd.DataFrame, tack_data: pd.DataFrame, 
                                min_distance: float, min_time: float, max_angle_tolerance: float) -> Dict:
    """
    Analyze the quality of segmentation based on current parameters
    
    Returns:
        Dict with quality metrics:
            - over_segmentation_score: 0-1 (1 = likely over-segmented)
            - segments_per_tack: average segments per tack
            - suggested_params: SegmentationParams for optimal segmentation
    """
    # Count segments per tack
    tacks = tack_data['tack'].unique()
    segments_per_tack = {tack: len(stretches[stretches['tack'] == tack]) for tack in tacks}
    
    # Check for over-segmentation
    max_segments_per_tack = max(segments_per_tack.values())
    total_segments = len(stretches)
    track_duration = (stretches['time'].max() - stretches['time'].min()).total_seconds() / 60  # in minutes
    track_distance = stretches['distance'].sum()  # total track distance
    
    # Calculate quality metrics
    ideal_segments = min(20, max(5, track_duration / 15))  # Roughly one segment per 15 minutes, between 5-20
    over_segmentation_score = min(1.0, total_segments / ideal_segments) if ideal_segments > 0 else 0
    
    # Suggest parameter adjustments if over-segmented
    if over_segmentation_score > 0.7 or max_segments_per_tack > 5:
        # Calculate scaling factor based on how over-segmented we are
        scaling_factor = math.log(max(1.5, total_segments / ideal_segments), 10) if ideal_segments > 0 else 1.5
        
        # Suggest new parameters
        suggested_min_distance = min_distance * scaling_factor
        suggested_min_time = min_time * scaling_factor
        suggested_angle_tolerance = max_angle_tolerance * (1 + (scaling_factor - 1) * 0.5)  # Less aggressive scaling for angle
        
        suggested_params = SegmentationParams(
            min_distance=suggested_min_distance,
            min_time=suggested_min_time,
            max_angle_tolerance=suggested_angle_tolerance,
            quality_score=1.0 - over_segmentation_score
        )
    else:
        suggested_params = SegmentationParams(
            min_distance=min_distance,
            min_time=min_time,
            max_angle_tolerance=max_angle_tolerance,
            quality_score=1.0 - over_segmentation_score
        )
    
    return {
        'over_segmentation_score': over_segmentation_score,
        'segments_per_tack': segments_per_tack,
        'max_segments_per_tack': max_segments_per_tack,
        'total_segments': total_segments,
        'ideal_segments': ideal_segments,
        'suggested_params': suggested_params
    }

def apply_optimized_parameters(st, quality_analysis):
    """
    Apply optimized parameters automatically in the UI and show notification
    
    Args:
        st: Streamlit session
        quality_analysis: Dict with quality metrics and suggested parameters
    """
    # Store original parameters for potential revert
    if 'original_parameters' not in st.session_state:
        st.session_state.original_parameters = {
            'min_distance': st.session_state.min_distance,
            'min_time': st.session_state.min_time,
            'max_angle_tolerance': st.session_state.max_angle_tolerance
        }
    
    # Apply new parameters
    st.session_state.min_distance = quality_analysis['suggested_params'].min_distance
    st.session_state.min_time = quality_analysis['suggested_params'].min_time
    st.session_state.max_angle_tolerance = quality_analysis['suggested_params'].max_angle_tolerance
    
    # Trigger recalculation with new parameters
    st.session_state.should_recalculate_segments = True
    
    # Show optimization notification
    st.success(f"Parameters automatically optimized to reduce segments from {quality_analysis['total_segments']} to approximately {quality_analysis['ideal_segments']}.")
```

### Automatic Optimization in UI
```python
def setup_parameter_controls(st):
    """Set up parameter controls with automatic optimization"""
    col1, col2, col3, col4 = st.columns([3, 3, 3, 2])
    
    with col1:
        min_distance = st.slider("Minimum Distance (m)", 5.0, 100.0, 
                                st.session_state.min_distance, 5.0,
                                key="min_distance_slider",
                                help="Minimum distance for a stretch to be considered")
    
    with col2:
        min_time = st.slider("Minimum Time (s)", 5.0, 60.0, 
                            st.session_state.min_time, 5.0,
                            key="min_time_slider",
                            help="Minimum time for a stretch to be considered")
    
    with col3:
        max_angle_tolerance = st.slider("Max Angle Tolerance (°)", 5.0, 30.0, 
                                        st.session_state.max_angle_tolerance, 1.0,
                                        key="max_angle_tolerance_slider",
                                        help="Maximum angle deviation allowed within a stretch")
    
    with col4:
        if 'original_parameters' in st.session_state:
            if st.button("Revert Parameters", help="Revert to original parameters before optimization"):
                # Restore original parameters
                st.session_state.min_distance = st.session_state.original_parameters['min_distance']
                st.session_state.min_time = st.session_state.original_parameters['min_time']
                st.session_state.max_angle_tolerance = st.session_state.original_parameters['max_angle_tolerance']
                
                # Clear original parameters storage
                del st.session_state.original_parameters
                
                # Trigger recalculation
                st.session_state.should_recalculate_segments = True
                st.experimental_rerun()
    
    # If we detect over-segmentation after calculation, show metrics
    if hasattr(st.session_state, 'segmentation_quality') and st.session_state.segmentation_quality['over_segmentation_score'] > 0.7:
        quality = st.session_state.segmentation_quality
        st.info(f"Segments: {quality['total_segments']} (Ideal: ~{int(quality['ideal_segments'])}), "
                f"Max segments on single tack: {quality['max_segments_per_tack']}")
```

### Service Layer Updates
```python
class SegmentService:
    # New methods for Phase 0
    def analyze_segmentation_quality(self, track: pd.DataFrame, current_params: Dict) -> Dict:
        """Analyze and return segmentation quality metrics"""
        pass
        
    def suggest_optimal_parameters(self, track: pd.DataFrame) -> Dict:
        """Suggest optimal segmentation parameters based on track characteristics"""
        pass
    
    def apply_optimal_parameters(self, track: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Automatically apply optimal segmentation parameters and return new segments"""
        pass
    
    # Methods for later phases
    def segment_track(self, track: pd.DataFrame, mode: str) -> List[TrackSegment]:
        """Segment a track using the appropriate strategy based on mode"""
        pass
        
    def detect_wind_shifts(self, track: pd.DataFrame) -> List[Tuple[datetime, float]]:
        """Detect potential wind shifts in a track"""
        pass
        
    def calculate_segment_confidence(self, segment: TrackSegment) -> float:
        """Calculate confidence score for a segment"""
        pass

class WindService:
    # New methods
    def estimate_wind_by_segment(self, segments: List[TrackSegment]) -> Dict[int, float]:
        """Estimate wind direction for each segment"""
        pass
        
    def detect_wind_shifts(self, track: pd.DataFrame) -> List[Tuple[datetime, float]]:
        """Detect wind direction shifts during a track"""
        pass
```

## Testing Plan

### Unit Tests
- Test segment consolidation with test_file_270_degrees.gpx (80+ segments)
- Test parameter scaling with tracks of various durations and distances
- Test segmentation algorithms with different track lengths
- Test wind shift detection with synthetic data
- Test outlier detection with known outliers

### Integration Tests
- Test end-to-end analysis flow with segmentation
- Test UI with different track modes
- Test visualization components with multi-segment data

### Performance Testing
- Benchmark segmentation algorithms with very large tracks
- Optimize computation for multi-segment analysis

## Phases and Timeline

### Week 1: Adaptive Parameter Scaling (Phase 0)
- Implement segment consolidation detection
- Build parameter scaling algorithms
- Create automatic parameter adjustment
- Integrate with existing UI

### Week 2: Core Infrastructure (Phase 1)
- Implement track segmentation strategies
- Build wind shift detection
- Enhance parameter scaling

### Week 3: Advanced Analysis (Phase 2)
- Implement statistical outlier filtering
- Build segment scoring system
- Update data models

### Week 4: User Interface (Phase 3)
- Create mode toggle and preset system
- Build segmentation controls
- Update visualizations

### Week 5: Testing and Refinement
- Comprehensive testing
- Performance optimization
- Documentation and finalization

## Future Enhancements
- Machine learning for wind pattern recognition
- Historical wind data integration
- Multi-session analysis to detect consistent patterns
- Weather API integration for validation
- Advanced report generation