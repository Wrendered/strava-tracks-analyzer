"""
Wind estimation algorithms - consolidated from multiple modules.

This module contains all wind estimation algorithms in one place for easy maintenance.
Each algorithm is well-documented and follows consistent interfaces.
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional, Tuple, List, Dict, Any
from sklearn.cluster import KMeans

from core.constants import (
    FULL_CIRCLE_DEGREES, UPWIND_DOWNWIND_BOUNDARY_DEGREES, ANGLE_WRAP_BOUNDARY_DEGREES,
    MIN_SEGMENTS_FOR_ESTIMATION, DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_MIN_SEGMENT_DISTANCE_METERS, MIN_RELIABLE_SEGMENT_LENGTH_METERS,
    HIGH_CONFIDENCE_MIN_DISTANCE_METERS, MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES,
    MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES, WIND_CONVERGENCE_THRESHOLD_DEGREES,
    WIND_SEARCH_RANGE_WIDTH_DEGREES, WIND_SEARCH_STEP_DEGREES,
    WIND_SEARCH_RANGE_DEGREES, MAX_KMEANS_CLUSTERS, KMEANS_N_INIT,
    MIN_SCORE_FOR_USER_GUIDED, MIN_SCORE_FOR_MULTI_ANGLE, ANGLE_CLUSTER_RANGE_DEGREES
)
from core.wind.models import WindEstimate
from core.metrics_advanced import calculate_segment_quality_score
from utils.segment_analysis import detect_suspicious_segments
from core.calculations import analyze_wind_angles

logger = logging.getLogger(__name__)


def calculate_wind_score(segments: pd.DataFrame, upwind_weight: float = 0.5, 
                        spread_weight: float = 0.3, balance_weight: float = 0.2) -> float:
    """
    Calculate a quality score for wind estimation based on sailing patterns.
    
    Args:
        segments: DataFrame with wind angle analysis results
        upwind_weight: Weight for port/starboard tack balance (0-1)
        spread_weight: Weight for consistency of upwind angles (0-1) 
        balance_weight: Weight for upwind/downwind balance (0-1)
        
    Returns:
        float: Quality score (0-1, higher is better)
    """
    upwind = segments[segments['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES]
    port_upwind = upwind[upwind['tack'] == 'Port']
    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
    
    # Calculate port/starboard balance (0-1, where 1 is perfect balance)
    if len(port_upwind) > 0 and len(starboard_upwind) > 0:
        tack_balance = min(len(port_upwind), len(starboard_upwind)) / max(len(port_upwind), len(starboard_upwind))
    else:
        tack_balance = 0
    
    # Calculate upwind/downwind balance
    upwind_downwind_balance = min(len(upwind), len(segments) - len(upwind)) / max(len(upwind), len(segments) - len(upwind), 1)
    
    # Calculate spread of upwind angles
    if len(upwind) >= MIN_SEGMENTS_FOR_ESTIMATION:
        upwind_spread = np.std(upwind['angle_to_wind'])
        # Normalize to 0-1 range (lower spread is better)
        normalized_spread = 1 - min(upwind_spread / WIND_SEARCH_RANGE_DEGREES, 1)
    else:
        normalized_spread = 0
    
    # Calculate weighted score
    score = (upwind_weight * tack_balance + 
             spread_weight * normalized_spread + 
             balance_weight * upwind_downwind_balance)
    
    return score


def calculate_angle_bisector(angle1: float, angle2: float) -> float:
    """
    Calculate the bisector of two angles, handling 0/360 degree wraparound.
    
    Args:
        angle1, angle2: Angles in degrees (0-360)
        
    Returns:
        float: Bisector angle in degrees (0-360)
    """
    # Handle angles crossing 0/360 boundary
    if abs(angle1 - angle2) > ANGLE_WRAP_BOUNDARY_DEGREES:
        if angle1 < angle2:
            angle1 += FULL_CIRCLE_DEGREES
        else:
            angle2 += FULL_CIRCLE_DEGREES
    
    bisector = (angle1 + angle2) / 2
    return bisector % FULL_CIRCLE_DEGREES


def estimate_wind_direction_iterative(
    segments: pd.DataFrame,
    initial_wind: float,
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE_METERS,
    max_iterations: int = 5
) -> WindEstimate:
    """
    FIXED: Estimate wind direction with proper iterative tack reclassification.
    
    This is the corrected algorithm that:
    1. Starts with an initial wind estimate
    2. Classifies segments as port/starboard based on current wind
    3. Calculates average angles for each tack
    4. Adjusts wind to balance the angles
    5. RECLASSIFIES segments with new wind estimate
    6. Repeats until convergence
    
    This fixes the major bug where segments were classified once and never
    reclassified, leading to unbalanced port/starboard angles.
    
    Args:
        segments: DataFrame with sailing segments (must have bearing, distance columns)
        initial_wind: Initial wind direction estimate (degrees)
        suspicious_angle_threshold: Minimum angle to wind to consider valid
        min_segment_distance: Minimum segment distance to consider
        max_iterations: Maximum iterations before giving up
        
    Returns:
        WindEstimate with balanced port/starboard angles
    """
    # Initialize result
    result = WindEstimate(
        direction=initial_wind,
        confidence="low",
        user_provided=True,
        port_angle=None,
        starboard_angle=None,
        port_count=0,
        starboard_count=0
    )
    
    # Validate input
    if segments is None or segments.empty:
        logger.warning("No segments provided for wind estimation")
        return result
    
    # Make a copy to avoid modifying original
    working_segments = segments.copy()
    
    # Track convergence
    current_wind = initial_wind
    previous_wind = None
    iteration_history = []
    
    logger.info(f"Starting iterative wind estimation with initial wind: {initial_wind:.1f}°")
    
    for iteration in range(max_iterations):
        logger.info(f"\n--- Iteration {iteration + 1} ---")
        
        # Step 1: Analyze segments with current wind estimate
        # This is the KEY FIX - we reclassify on each iteration!
        analyzed = analyze_wind_angles(working_segments, current_wind)
        
        # Step 2: Filter to upwind segments only
        upwind = analyzed[analyzed['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES].copy()
        
        # Step 3: Filter out suspicious segments
        if len(upwind) > 0:
            suspicious_segments = detect_suspicious_segments(
                upwind,
                min_angle_to_wind=suspicious_angle_threshold,
                min_segment_length=MIN_RELIABLE_SEGMENT_LENGTH_METERS
            )
            upwind_filtered = suspicious_segments[~suspicious_segments['suspicious']]
            
            if len(suspicious_segments) > len(upwind_filtered):
                logger.info(f"Filtered out {len(suspicious_segments) - len(upwind_filtered)} suspicious segments")
            
            upwind = upwind_filtered
        
        # Step 4: Apply minimum distance filter
        if min_segment_distance > 0 and len(upwind) > 0:
            upwind = upwind[upwind['distance'] >= min_segment_distance]
            logger.info(f"Using {len(upwind)} upwind segments with distance >= {min_segment_distance}m")
        
        # Check if we have enough segments
        if len(upwind) < MIN_SEGMENTS_FOR_ESTIMATION:
            logger.warning(f"Insufficient upwind segments ({len(upwind)}) for estimation")
            if iteration == 0:
                return result  # Failed on first iteration
            else:
                break  # Use previous iteration's result
        
        # Step 5: Split by tack (using current wind's classification)
        port_tack = upwind[upwind['tack'] == 'Port']
        starboard_tack = upwind[upwind['tack'] == 'Starboard']
        
        logger.info(f"Tack distribution: Port={len(port_tack)}, Starboard={len(starboard_tack)}")
        
        # Need at least one segment in each tack
        if len(port_tack) == 0 or len(starboard_tack) == 0:
            logger.warning("Missing one tack, cannot balance")
            if iteration == 0:
                return result
            else:
                break
        
        # Step 6: Calculate weighted average angles for each tack
        # Use median for robustness against outliers
        port_angles = port_tack['angle_to_wind'].values
        starboard_angles = starboard_tack['angle_to_wind'].values
        
        # Use median for robustness
        port_median = np.median(port_angles)
        starboard_median = np.median(starboard_angles)
        
        # Also calculate weighted averages for comparison
        port_weights = port_tack['distance'].values
        starboard_weights = starboard_tack['distance'].values
        
        port_weighted_avg = np.average(port_angles, weights=port_weights)
        starboard_weighted_avg = np.average(starboard_angles, weights=starboard_weights)
        
        logger.info(f"Port angles: median={port_median:.1f}°, weighted_avg={port_weighted_avg:.1f}°")
        logger.info(f"Starboard angles: median={starboard_median:.1f}°, weighted_avg={starboard_weighted_avg:.1f}°")
        
        # Step 7: Calculate wind adjustment to balance angles
        # Use median for more robust estimation
        angle_imbalance = starboard_median - port_median
        wind_adjustment = angle_imbalance / 2.0
        
        # Calculate new wind estimate
        new_wind = (current_wind - wind_adjustment) % FULL_CIRCLE_DEGREES
        
        logger.info(f"Angle imbalance: {angle_imbalance:.1f}°, Wind adjustment: {wind_adjustment:.1f}°")
        logger.info(f"New wind estimate: {new_wind:.1f}° (was {current_wind:.1f}°)")
        
        # Track iteration history
        iteration_history.append({
            'iteration': iteration + 1,
            'wind': new_wind,
            'port_median': port_median,
            'starboard_median': starboard_median,
            'imbalance': abs(angle_imbalance),
            'port_count': len(port_tack),
            'starboard_count': len(starboard_tack)
        })
        
        # Step 8: Check for convergence
        if abs(new_wind - current_wind) < WIND_CONVERGENCE_THRESHOLD_DEGREES:
            logger.info(f"✓ Converged! Wind direction stabilized at {new_wind:.1f}°")
            current_wind = new_wind
            break
        
        # Check if we're oscillating
        if previous_wind is not None and abs(new_wind - previous_wind) < WIND_CONVERGENCE_THRESHOLD_DEGREES:
            logger.info(f"✓ Detected oscillation, taking average of last two estimates")
            current_wind = (current_wind + new_wind) / 2.0
            break
        
        # Update for next iteration
        previous_wind = current_wind
        current_wind = new_wind
    
    # Final analysis with converged wind direction
    final_analyzed = analyze_wind_angles(working_segments, current_wind)
    final_upwind = final_analyzed[final_analyzed['angle_to_wind'] < UPWIND_DOWNWIND_BOUNDARY_DEGREES]
    
    # Apply same filtering as in iterations
    if len(final_upwind) > 0:
        suspicious_segments = detect_suspicious_segments(
            final_upwind,
            min_angle_to_wind=suspicious_angle_threshold,
            min_segment_length=MIN_RELIABLE_SEGMENT_LENGTH_METERS
        )
        final_upwind = suspicious_segments[~suspicious_segments['suspicious']]
    
    if min_segment_distance > 0 and len(final_upwind) > 0:
        final_upwind = final_upwind[final_upwind['distance'] >= min_segment_distance]
    
    # Get final statistics
    final_port = final_upwind[final_upwind['tack'] == 'Port']
    final_starboard = final_upwind[final_upwind['tack'] == 'Starboard']
    
    # Calculate final angles
    port_angle = None
    starboard_angle = None
    
    if len(final_port) > 0:
        port_angle = np.median(final_port['angle_to_wind'].values)
    
    if len(final_starboard) > 0:
        starboard_angle = np.median(final_starboard['angle_to_wind'].values)
    
    # Determine confidence level
    confidence = "low"
    if port_angle is not None and starboard_angle is not None:
        final_imbalance = abs(port_angle - starboard_angle)
        total_distance = final_upwind['distance'].sum()
        
        # High confidence if well-balanced and sufficient data
        if (final_imbalance < MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES and 
            len(final_port) >= MIN_SEGMENTS_FOR_ESTIMATION and 
            len(final_starboard) >= MIN_SEGMENTS_FOR_ESTIMATION and
            total_distance > HIGH_CONFIDENCE_MIN_DISTANCE_METERS):
            confidence = "high"
        elif final_imbalance < MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES:
            confidence = "medium"
    
    # Log final results
    logger.info(f"\n--- Final Results ---")
    logger.info(f"Converged wind direction: {current_wind:.1f}°")
    logger.info(f"Final port angle: {port_angle:.1f}° ({len(final_port)} segments)" if port_angle else "No port segments")
    logger.info(f"Final starboard angle: {starboard_angle:.1f}° ({len(final_starboard)} segments)" if starboard_angle else "No starboard segments")
    if port_angle and starboard_angle:
        logger.info(f"Final angle balance: {abs(port_angle - starboard_angle):.1f}° difference")
    logger.info(f"Confidence: {confidence}")
    
    # Return result
    return WindEstimate(
        direction=current_wind,
        confidence=confidence,
        user_provided=False,
        port_angle=port_angle,
        starboard_angle=starboard_angle,
        port_count=len(final_port),
        starboard_count=len(final_starboard)
    )


def estimate_wind_direction_weighted(
    stretches: pd.DataFrame,
    user_wind_direction: float,
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE_METERS
) -> WindEstimate:
    """
    LEGACY: Distance-weighted wind estimation (single iteration).
    
    This is the old algorithm that has the tack classification bug.
    It's kept for compatibility but you should use estimate_wind_direction_iterative instead.
    """
    logger.warning("Using legacy single-iteration wind estimation. Consider using estimate_wind_direction_iterative for better results.")
    
    # Just call the iterative version with max_iterations=1 to get the old behavior
    return estimate_wind_direction_iterative(
        stretches,
        user_wind_direction,
        suspicious_angle_threshold=suspicious_angle_threshold,
        min_segment_distance=min_segment_distance,
        max_iterations=1
    )


def user_guided_wind_estimation(segments: pd.DataFrame, user_wind_direction: float) -> Tuple[Optional[float], float]:
    """
    Estimate wind direction using user input as starting point.
    
    Tests multiple candidate directions around the user's estimate and
    selects the one that produces the most balanced sailing patterns.
    
    Args:
        segments: DataFrame of sailing segments
        user_wind_direction: User-provided wind direction (degrees)
        
    Returns:
        tuple: (estimated_wind_direction, quality_score) or (None, 0) if insufficient quality
    """
    logger.info(f"Starting user-guided estimation with {user_wind_direction}° as reference")
    
    # Generate candidate angles around user's estimate
    range_width = WIND_SEARCH_RANGE_WIDTH_DEGREES
    step_size = WIND_SEARCH_STEP_DEGREES
    num_steps = range_width // step_size + 1
    candidate_offsets = np.linspace(-range_width/2, range_width/2, num_steps)
    
    # Add exact user direction and intermediate values
    candidate_winds = [(round(user_wind_direction + offset)) % FULL_CIRCLE_DEGREES for offset in candidate_offsets]
    
    # Add intermediate precision points
    intermediate_offsets = [5, -5, 15, -15, 25, -25]
    for offset in intermediate_offsets:
        candidate_winds.append((round(user_wind_direction + offset)) % FULL_CIRCLE_DEGREES)
    
    # Remove duplicates and test each candidate
    candidate_winds = sorted(list(set(candidate_winds)))
    candidate_scores = []
    
    for wind in candidate_winds:
        test_result = analyze_wind_angles(segments.copy(), wind)
        score = calculate_wind_score(test_result)
        candidate_scores.append((wind, score))
        logger.debug(f"Wind candidate {wind}° - Score: {score:.2f}")
    
    # Select best candidate
    best_candidate = max(candidate_scores, key=lambda x: x[1])
    best_wind, best_score = best_candidate
    
    logger.info(f"Best user-guided candidate: {best_wind:.1f}° (score: {best_score:.2f})")
    
    if best_score > MIN_SCORE_FOR_USER_GUIDED:
        return best_wind, best_score
    else:
        return None, best_score


def bearing_cluster_analysis(segments: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Analyze sailing bearings using clustering to find dominant directions.
    
    Uses KMeans clustering on bearing vectors to identify the main sailing
    directions, then finds the most opposite pair.
    
    Args:
        segments: DataFrame of sailing segments with 'bearing' column
        
    Returns:
        tuple: (angle1, angle2, max_angular_difference) of most opposite bearings
    """
    bearings = segments['bearing'].values
    
    # Convert bearings to unit circle coordinates for proper clustering
    x = np.cos(np.radians(bearings))
    y = np.sin(np.radians(bearings))
    
    # Use KMeans to find bearing clusters
    n_clusters = min(MAX_KMEANS_CLUSTERS, len(segments) - 1)
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=KMEANS_N_INIT)
    kmeans.fit(np.column_stack([x, y]))
    
    # Convert cluster centers back to angles
    centers = kmeans.cluster_centers_
    center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0]))) % FULL_CIRCLE_DEGREES
    
    # Count points in each cluster and find top clusters
    cluster_counts = [np.sum(kmeans.labels_ == i) for i in range(len(center_angles))]
    sorted_clusters = sorted(range(len(cluster_counts)), key=lambda i: cluster_counts[i], reverse=True)
    top_clusters = sorted_clusters[:min(3, len(sorted_clusters))]
    
    # Find the most opposite pair among top clusters
    max_diff = -1
    angle1 = angle2 = 0
    
    for i in range(len(top_clusters)):
        for j in range(i+1, len(top_clusters)):
            idx1, idx2 = top_clusters[i], top_clusters[j]
            angle_i, angle_j = center_angles[idx1], center_angles[idx2]
            
            # Calculate angular difference (minimum of clockwise/counterclockwise)
            diff = abs(angle_i - angle_j)
            diff = min(diff, FULL_CIRCLE_DEGREES - diff)
            
            if diff > max_diff:
                max_diff = diff
                angle1, angle2 = angle_i, angle_j
    
    logger.info(f"Cluster analysis found most opposite bearings: {angle1:.1f}° and {angle2:.1f}° (diff: {max_diff:.1f}°)")
    return angle1, angle2, max_diff