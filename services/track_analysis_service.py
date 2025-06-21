"""
Shared track analysis service.

This module provides a unified analysis pipeline that ensures consistent
results between the main analysis page and bulk upload functionality.
"""

import pandas as pd
import logging
import math
import uuid
from typing import Dict, Any, Optional, Tuple

from core.gpx import load_gpx_file
from core.segments import find_consistent_angle_stretches
from core.calculations import analyze_wind_angles
from core.wind.factory import estimate_wind_direction_factory, WindEstimationParams
from core.metrics_advanced import calculate_vmg_upwind
from core.models.gear_item import GearItem
from config.settings import DEFAULT_MIN_DISTANCE, DEFAULT_MIN_DURATION, DEFAULT_MIN_SPEED

logger = logging.getLogger(__name__)


class TrackAnalysisResult:
    """Container for track analysis results."""
    
    def __init__(self, 
                 track_data: pd.DataFrame,
                 segments: pd.DataFrame, 
                 metadata: Dict[str, Any],
                 initial_wind: float,
                 refined_wind: float,
                 wind_confidence: str,
                 filename: str):
        self.track_data = track_data
        self.segments = segments
        self.metadata = metadata
        self.initial_wind = initial_wind
        self.refined_wind = refined_wind
        self.wind_confidence = wind_confidence
        self.filename = filename
        
        # Calculate derived metrics
        self._calculate_summary_metrics()
    
    def _calculate_summary_metrics(self) -> None:
        """Calculate summary metrics from segments."""
        if self.segments.empty:
            self.upwind_segments = pd.DataFrame()
            self.downwind_segments = pd.DataFrame()
            self.vmg_upwind = None
            self.best_port_angle = None
            self.best_starboard_angle = None
            self.total_distance = 0
            self.avg_speed = 0
            self.max_speed = 0
            return
        
        # Split segments using the same method as main page
        self.upwind_segments = self.segments[self.segments.get('direction', '').str.lower() == 'upwind'] if 'direction' in self.segments.columns else pd.DataFrame()
        self.downwind_segments = self.segments[self.segments.get('direction', '').str.lower() == 'downwind'] if 'direction' in self.segments.columns else pd.DataFrame()
        
        # Calculate VMG with segment IDs
        self.vmg_upwind = None
        self.vmg_segment_ids = []
        if not self.upwind_segments.empty:
            self.vmg_upwind, self.vmg_segment_ids = calculate_vmg_upwind(self.upwind_segments, return_segment_ids=True)
        
        # Get best angles
        self.best_port_angle = None
        self.best_starboard_angle = None
        self.best_port_speed = None
        self.best_starboard_speed = None
        
        if not self.upwind_segments.empty:
            port_upwind = self.upwind_segments[self.upwind_segments['tack'] == 'Port']
            starboard_upwind = self.upwind_segments[self.upwind_segments['tack'] == 'Starboard']
            
            if not port_upwind.empty:
                best_port_idx = port_upwind['angle_to_wind'].idxmin()
                self.best_port_angle = port_upwind.loc[best_port_idx, 'angle_to_wind']
                self.best_port_speed = port_upwind.loc[best_port_idx, 'avg_speed_knots']
            
            if not starboard_upwind.empty:
                best_starboard_idx = starboard_upwind['angle_to_wind'].idxmin()
                self.best_starboard_angle = starboard_upwind.loc[best_starboard_idx, 'angle_to_wind']
                self.best_starboard_speed = starboard_upwind.loc[best_starboard_idx, 'avg_speed_knots']
        
        # Basic metrics
        self.total_distance = self.segments['distance'].sum() / 1000 if 'distance' in self.segments.columns else 0
        self.avg_speed = self.segments['avg_speed_knots'].mean() if 'avg_speed_knots' in self.segments.columns else 0
        self.max_speed = self.segments['avg_speed_knots'].max() if 'avg_speed_knots' in self.segments.columns else 0
        self.avg_upwind_angle = self.upwind_segments['angle_to_wind'].mean() if not self.upwind_segments.empty else None


def analyze_track_data(track_data: pd.DataFrame,
                      initial_wind_direction: float,
                      filename: str = "current_track.gpx",
                      metadata: Optional[Dict[str, Any]] = None,
                      angle_tolerance: float = 25,
                      min_distance: float = DEFAULT_MIN_DISTANCE,
                      min_duration: float = DEFAULT_MIN_DURATION, 
                      min_speed: float = DEFAULT_MIN_SPEED,
                      suspicious_angle_threshold: float = 20) -> TrackAnalysisResult:
    """
    Analyze track data that's already loaded into a DataFrame.
    
    This function provides the exact same analysis pipeline as analyze_track_file
    but works with data already in memory (e.g., from session state).
    
    Args:
        track_data: DataFrame containing track data
        initial_wind_direction: Initial wind direction estimate in degrees
        filename: Name for the track (for display purposes)
        metadata: Optional metadata dict
        angle_tolerance: Angle tolerance for segment detection
        min_distance: Minimum segment distance in meters
        min_duration: Minimum segment duration in seconds  
        min_speed: Minimum speed filter in knots
        suspicious_angle_threshold: Threshold for wind estimation
        
    Returns:
        TrackAnalysisResult: Complete analysis results
        
    Raises:
        Exception: If analysis fails
    """
    if metadata is None:
        metadata = {}
    
    try:
        logger.info(f"Analyzing track data for {filename} with {len(track_data)} points")
        
        # Step 2: Detect segments (same as main page)
        segments = find_consistent_angle_stretches(
            track_data, 
            angle_tolerance,
            min_duration,
            min_distance
        )
        logger.info(f"Found {len(segments)} initial segments")
        
        # Step 3: Filter by speed (same as main page)
        if not segments.empty:
            segments = segments[segments['avg_speed_knots'] >= min_speed]
            logger.info(f"After speed filter: {len(segments)} segments")
        
        if segments.empty:
            logger.warning(f"No segments found for {filename}")
            return TrackAnalysisResult(
                track_data=track_data,
                segments=pd.DataFrame(),
                metadata=metadata,
                initial_wind=initial_wind_direction,
                refined_wind=initial_wind_direction,
                wind_confidence='None',
                filename=filename
            )
        
        # Step 4: Estimate wind direction using factory pattern
        wind_params = WindEstimationParams(
            suspicious_angle_threshold=suspicious_angle_threshold,
            min_segment_distance=min_distance
        )
        wind_estimate = estimate_wind_direction_factory(
            segments,
            initial_wind=initial_wind_direction,
            method='iterative',  # Use best algorithm
            params=wind_params
        )
        
        refined_wind = wind_estimate.direction
        logger.info(f"Wind direction: {initial_wind_direction}° → {refined_wind:.1f}°")
        
        # Step 5: Analyze with refined wind (same as main page)
        segments = analyze_wind_angles(segments, refined_wind)
        
        # Step 6: Add sailing_type column (same as main page)
        if 'direction' in segments.columns and 'tack' in segments.columns:
            segments['sailing_type'] = segments['direction'] + ' ' + segments['tack']
        
        logger.info(f"Successfully analyzed {filename}: {len(segments)} segments")
        
        return TrackAnalysisResult(
            track_data=track_data,
            segments=segments,
            metadata=metadata,
            initial_wind=initial_wind_direction,
            refined_wind=refined_wind,
            wind_confidence=wind_estimate.confidence,
            filename=filename
        )
        
    except Exception as e:
        logger.error(f"Error analyzing {filename}: {e}")
        raise


def analyze_track_file(file, 
                      initial_wind_direction: float,
                      angle_tolerance: float = 25,
                      min_distance: float = DEFAULT_MIN_DISTANCE,
                      min_duration: float = DEFAULT_MIN_DURATION, 
                      min_speed: float = DEFAULT_MIN_SPEED,
                      suspicious_angle_threshold: float = 20) -> TrackAnalysisResult:
    """
    Analyze a single track file using the standard pipeline.
    
    This function loads a GPX file and delegates to analyze_track_data
    for consistent analysis across all parts of the application.
    
    Args:
        file: File object or file path to analyze
        initial_wind_direction: Initial wind direction estimate in degrees
        angle_tolerance: Angle tolerance for segment detection
        min_distance: Minimum segment distance in meters
        min_duration: Minimum segment duration in seconds  
        min_speed: Minimum speed filter in knots
        suspicious_angle_threshold: Threshold for wind estimation
        
    Returns:
        TrackAnalysisResult: Complete analysis results
        
    Raises:
        Exception: If analysis fails
    """
    filename = getattr(file, 'name', str(file))
    
    try:
        # Step 1: Load GPX file
        track_data, metadata = load_gpx_file(file)
        logger.info(f"Loaded {filename} with {len(track_data)} points")
        
        # Step 2: Delegate to analyze_track_data for consistent processing
        return analyze_track_data(
            track_data=track_data,
            initial_wind_direction=initial_wind_direction,
            filename=filename,
            metadata=metadata,
            angle_tolerance=angle_tolerance,
            min_distance=min_distance,
            min_duration=min_duration,
            min_speed=min_speed,
            suspicious_angle_threshold=suspicious_angle_threshold
        )
        
    except Exception as e:
        logger.error(f"Error analyzing {filename}: {e}")
        raise


def create_gear_item_from_analysis(analysis_result: TrackAnalysisResult, 
                                  gear_name: Optional[str] = None) -> GearItem:
    """
    Create a GearItem from analysis results.
    
    Args:
        analysis_result: Results from analyze_track_file()
        gear_name: Optional name for the gear item
        
    Returns:
        GearItem: Gear item ready for comparison
    """
    if gear_name is None:
        gear_name = analysis_result.filename.replace('.gpx', '')
    
    # Calculate upwind progress speed (legacy metric)
    upwind_progress_speed = None
    if (analysis_result.best_port_angle and analysis_result.best_starboard_angle and 
        analysis_result.best_port_speed and analysis_result.best_starboard_speed):
        avg_angle = (analysis_result.best_port_angle + analysis_result.best_starboard_angle) / 2
        avg_speed = (analysis_result.best_port_speed + analysis_result.best_starboard_speed) / 2
        upwind_progress_speed = avg_speed * math.cos(math.radians(avg_angle))
    
    return GearItem(
        id=str(uuid.uuid4()),
        title=gear_name,
        track_name=analysis_result.filename,
        wind_direction=analysis_result.refined_wind,
        avg_speed=analysis_result.avg_speed,
        max_speed=analysis_result.max_speed,
        distance=analysis_result.total_distance,
        vmg_upwind=analysis_result.vmg_upwind,
        upwind_progress_speed=upwind_progress_speed,
        best_port_upwind_angle=analysis_result.best_port_angle,
        best_port_upwind_speed=analysis_result.best_port_speed,
        best_starboard_upwind_angle=analysis_result.best_starboard_angle,
        best_starboard_upwind_speed=analysis_result.best_starboard_speed,
        avg_upwind_angle=analysis_result.avg_upwind_angle,
        source_file=analysis_result.filename
    )


def get_analysis_parameters_from_session(session_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract analysis parameters from session state.
    
    Args:
        session_state: Streamlit session state
        
    Returns:
        Dict with analysis parameters
    """
    return {
        'angle_tolerance': session_state.get('angle_tolerance', 25),
        'min_distance': session_state.get('min_distance', DEFAULT_MIN_DISTANCE),
        'min_duration': session_state.get('min_duration', DEFAULT_MIN_DURATION),
        'min_speed': session_state.get('min_speed', DEFAULT_MIN_SPEED),
        'suspicious_angle_threshold': session_state.get('suspicious_angle_threshold', 20)
    }