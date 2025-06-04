"""
Wind direction estimation orchestrator.

This module provides the main entry point for wind direction estimation,
coordinating between different estimation methods in a clean, testable way.
"""

import logging
from core.constants import MIN_SEGMENTS_FOR_ESTIMATION, DISTANCE_QUANTILE_THRESHOLD, DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
from core.wind_estimation_methods import (
    user_guided_wind_estimation,
    bearing_cluster_analysis, 
    generate_wind_candidates,
    multi_candidate_wind_estimation,
    fallback_bisector_method
)

logger = logging.getLogger(__name__)


def validate_and_filter_segments(segments):
    """
    Validate input segments and filter to good quality data.
    
    Args:
        segments: DataFrame of sailing segments
        
    Returns:
        DataFrame: Filtered segments or None if insufficient data
    """
    if len(segments) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning(f"Not enough segments to estimate wind direction (need at least {MIN_SEGMENTS_FOR_ESTIMATION})")
        return None
    
    # Filter to segments with good distance and speed
    min_distance_threshold = segments['distance'].quantile(DISTANCE_QUANTILE_THRESHOLD)
    good_segments = segments[segments['distance'] > min_distance_threshold]
    
    # Sort by distance to prioritize longer segments
    good_segments = good_segments.sort_values('distance', ascending=False)
    
    if len(good_segments) < MIN_SEGMENTS_FOR_ESTIMATION:
        logger.warning("Not enough good quality segments to estimate wind direction")
        return None
    
    logger.info(f"Using {len(good_segments)} good quality segments for wind estimation")
    return good_segments


def estimate_wind_direction_orchestrated(segments, use_simple_method=True, user_wind_direction=None):
    """
    Estimate wind direction using a coordinated multi-method approach.
    
    This function orchestrates different wind estimation methods in priority order:
    1. Simple iterative method (if requested and user wind provided)
    2. User-guided candidate testing (if user wind provided)
    3. Multi-candidate testing from bearing analysis
    4. Upwind tack refinement
    5. Fallback bisector method
    
    Args:
        segments: DataFrame of consistent sailing segments
        use_simple_method: If True, tries simplified iterative method first
        user_wind_direction: Optional user-provided wind direction
        
    Returns:
        float: Estimated wind direction in degrees, or None if estimation fails
    """
    logger.info("Starting orchestrated wind direction estimation")
    
    # Validate and filter input segments
    good_segments = validate_and_filter_segments(segments)
    if good_segments is None:
        return user_wind_direction  # Return user input as fallback
    
    # METHOD 1: Simple iterative method (if enabled and user wind provided)
    if use_simple_method and user_wind_direction is not None:
        try:
            from utils.simplified_wind_estimation import iterative_wind_estimation
            
            estimated_wind = iterative_wind_estimation(
                segments.copy(),
                user_wind_direction,
                suspicious_angle_threshold=DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
                max_iterations=3
            )
            
            if estimated_wind is not None:
                logger.info(f"✓ Simple iterative method succeeded: {estimated_wind:.1f}°")
                return estimated_wind
                
        except Exception as e:
            logger.error(f"Simple iterative method failed: {e}")
    
    # METHOD 2: User-guided estimation (if user wind provided)
    if user_wind_direction is not None:
        user_guided_result, score = user_guided_wind_estimation(good_segments, user_wind_direction)
        if user_guided_result is not None:
            logger.info(f"✓ User-guided estimation succeeded: {user_guided_result:.1f}° (score: {score:.2f})")
            return user_guided_result
    
    # METHOD 3: Multi-candidate testing
    # First, analyze bearing clusters
    angle1, angle2, max_diff = bearing_cluster_analysis(good_segments)
    
    # Generate candidate wind directions
    candidates = generate_wind_candidates(
        good_segments, 
        user_wind_direction=user_wind_direction,
        bearing_clusters=(angle1, angle2, max_diff)
    )
    
    # Test all candidates
    best_wind, best_score = multi_candidate_wind_estimation(good_segments, candidates)
    
    if best_wind is not None:
        logger.info(f"✓ Multi-candidate testing succeeded: {best_wind:.1f}° (score: {best_score:.2f})")
        
        # METHOD 4: Try upwind tack refinement
        try:
            from utils.analysis import estimate_wind_direction_from_upwind_tacks, analyze_wind_angles
            
            # Analyze with the best wind from multi-candidate testing
            refined_segments = analyze_wind_angles(good_segments.copy(), best_wind)
            refined_wind = estimate_wind_direction_from_upwind_tacks(refined_segments)
            
            if refined_wind is not None:
                logger.info(f"✓ Upwind tack refinement succeeded: {refined_wind:.1f}°")
                return refined_wind
            
        except Exception as e:
            logger.warning(f"Upwind tack refinement failed: {e}")
        
        # Return the multi-candidate result if refinement fails
        return best_wind
    
    # METHOD 5: Fallback bisector method
    fallback_wind = fallback_bisector_method(angle1, angle2, max_diff)
    if fallback_wind is not None:
        logger.info(f"✓ Fallback bisector method: {fallback_wind:.1f}°")
        return fallback_wind
    
    # Final fallback to user input
    if user_wind_direction is not None:
        logger.warning(f"All estimation methods failed, using user-provided: {user_wind_direction}°")
        return user_wind_direction
    
    logger.error("Wind direction estimation completely failed")
    return None