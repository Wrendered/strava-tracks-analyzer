"""
Wind estimation methods - broken down from the monolithic estimate_wind_direction function.

This module contains focused, single-responsibility functions for different wind estimation approaches.
Each method is tested and validated independently before being composed into the main estimation workflow.
"""

import numpy as np
import logging
from sklearn.cluster import KMeans
from core.constants import (
    FULL_CIRCLE_DEGREES, UPWIND_DOWNWIND_BOUNDARY_DEGREES, ANGLE_WRAP_BOUNDARY_DEGREES,
    MIN_SEGMENTS_FOR_ESTIMATION, WIND_SEARCH_RANGE_WIDTH_DEGREES, WIND_SEARCH_STEP_DEGREES,
    WIND_SEARCH_RANGE_DEGREES, MAX_KMEANS_CLUSTERS, KMEANS_N_INIT,
    MIN_SCORE_FOR_USER_GUIDED, MIN_SCORE_FOR_MULTI_ANGLE, ANGLE_CLUSTER_RANGE_DEGREES
)

logger = logging.getLogger(__name__)


def calculate_wind_score(segments, upwind_weight=0.5, spread_weight=0.3, balance_weight=0.2):
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


def user_guided_wind_estimation(segments, user_wind_direction):
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
    from utils.analysis import analyze_wind_angles  # Import here to avoid circular deps
    
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


def bearing_cluster_analysis(segments):
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


def generate_wind_candidates(segments, user_wind_direction=None, bearing_clusters=None):
    """
    Generate candidate wind directions for testing.
    
    Creates candidates from multiple sources:
    - Angles off the main bearing clusters
    - Bisector of opposite bearings
    - User wind direction variations
    
    Args:
        segments: DataFrame of sailing segments
        user_wind_direction: Optional user-provided wind direction
        bearing_clusters: Optional tuple from bearing_cluster_analysis()
        
    Returns:
        list: Unique candidate wind directions (degrees)
    """
    candidate_winds = []
    
    # If no bearing clusters provided, calculate them
    if bearing_clusters is None:
        angle1, angle2, max_diff = bearing_cluster_analysis(segments)
    else:
        angle1, angle2, max_diff = bearing_clusters
    
    # Get cluster center angles for additional candidates
    bearings = segments['bearing'].values
    x = np.cos(np.radians(bearings))
    y = np.sin(np.radians(bearings))
    n_clusters = min(MAX_KMEANS_CLUSTERS, len(segments) - 1)
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=KMEANS_N_INIT)
    kmeans.fit(np.column_stack([x, y]))
    centers = kmeans.cluster_centers_
    center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0]))) % FULL_CIRCLE_DEGREES
    
    # Generate candidates from bearing clusters at various angles
    for bearing in center_angles:
        for angle_off in [30, 60, 90, 120, 150]:
            candidate_winds.extend([
                (bearing + angle_off) % FULL_CIRCLE_DEGREES,
                (bearing - angle_off) % FULL_CIRCLE_DEGREES
            ])
    
    # Add bisector-based candidates if we have opposite bearings
    if max_diff > UPWIND_DOWNWIND_BOUNDARY_DEGREES:
        bisector = calculate_angle_bisector(angle1, angle2)
        candidate_winds.extend([
            bisector,
            (bisector + UPWIND_DOWNWIND_BOUNDARY_DEGREES) % FULL_CIRCLE_DEGREES,
            (bisector + ANGLE_WRAP_BOUNDARY_DEGREES) % FULL_CIRCLE_DEGREES,
            (bisector + 270) % FULL_CIRCLE_DEGREES
        ])
    
    # Add user wind direction variations
    if user_wind_direction is not None:
        candidate_winds.extend([
            user_wind_direction,
            (user_wind_direction + ANGLE_CLUSTER_RANGE_DEGREES) % FULL_CIRCLE_DEGREES,
            (user_wind_direction - ANGLE_CLUSTER_RANGE_DEGREES) % FULL_CIRCLE_DEGREES
        ])
    
    # Remove duplicates and normalize
    candidate_winds = [(w % FULL_CIRCLE_DEGREES) for w in candidate_winds]
    return sorted(list(set(candidate_winds)))


def calculate_angle_bisector(angle1, angle2):
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


def multi_candidate_wind_estimation(segments, candidates):
    """
    Test multiple wind direction candidates and select the best one.
    
    Args:
        segments: DataFrame of sailing segments
        candidates: List of candidate wind directions to test
        
    Returns:
        tuple: (best_wind_direction, best_score) or (None, 0) if no good candidates
    """
    from utils.analysis import analyze_wind_angles  # Import here to avoid circular deps
    
    candidate_scores = []
    
    for wind in candidates:
        test_result = analyze_wind_angles(segments.copy(), wind)
        score = calculate_wind_score(test_result)
        candidate_scores.append((wind, score))
    
    if not candidate_scores:
        return None, 0
    
    # Select the candidate with highest score
    best_candidate = max(candidate_scores, key=lambda x: x[1])
    best_wind, best_score = best_candidate
    
    logger.info(f"Best wind from multi-candidate testing: {best_wind:.1f}° (score: {best_score:.2f})")
    
    if best_score > MIN_SCORE_FOR_MULTI_ANGLE:
        return best_wind, best_score
    else:
        return None, best_score


def fallback_bisector_method(angle1, angle2, max_diff):
    """
    Fallback wind estimation using bisector of opposite bearings.
    
    Args:
        angle1, angle2: Two opposite bearing angles  
        max_diff: Angular difference between them
        
    Returns:
        float: Estimated wind direction or None if insufficient data
    """
    if max_diff <= UPWIND_DOWNWIND_BOUNDARY_DEGREES:
        return None
    
    bisector = calculate_angle_bisector(angle1, angle2)
    
    # Test both the bisector and perpendicular to it
    bisector_wind = bisector
    perpendicular_wind = (bisector + UPWIND_DOWNWIND_BOUNDARY_DEGREES) % FULL_CIRCLE_DEGREES
    
    logger.info(f"Fallback bisector method: {bisector_wind:.1f}° or {perpendicular_wind:.1f}°")
    
    # Default to perpendicular (traditional sailing assumption)
    return perpendicular_wind