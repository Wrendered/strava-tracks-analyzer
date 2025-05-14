"""
Wind estimator module.

This module provides a unified interface for wind direction estimation,
supporting multiple estimation strategies and methods.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Protocol
from dataclasses import dataclass, field

from core.wind.models import WindEstimate
from config.settings import (
    DEFAULT_WIND_DIRECTION,
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_MIN_SEGMENT_DISTANCE,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_CONVERGENCE_THRESHOLD
)

logger = logging.getLogger(__name__)


class EstimationStrategy(Protocol):
    """Protocol defining the interface for wind estimation strategies."""
    
    def estimate(
        self, 
        segments: pd.DataFrame,
        initial_direction: float,
        **kwargs
    ) -> WindEstimate:
        """Estimate wind direction from segments."""
        ...


class BasicStrategy:
    """
    Basic wind direction estimation strategy.
    
    This strategy uses a simple average of port and starboard tack angles
    to estimate the wind direction.
    """
    
    def estimate(
        self, 
        segments: pd.DataFrame,
        initial_direction: float,
        suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
        **kwargs
    ) -> WindEstimate:
        """
        Estimate wind direction using basic angle averaging.
        
        Args:
            segments: DataFrame with segments
            initial_direction: Initial wind direction estimate
            suspicious_angle_threshold: Threshold for suspicious angles
            **kwargs: Additional keyword arguments
            
        Returns:
            WindEstimate: Estimated wind direction
        """
        # Make a copy to avoid modifying the original
        df = segments.copy()
        
        # Filter out suspicious segments
        df = df[df['angle_to_wind'] >= suspicious_angle_threshold]
        
        # Split by tack
        port_tack = df[df['tack'] == 'Port']
        starboard_tack = df[df['tack'] == 'Starboard']
        
        # Check if we have both tacks
        has_both_tacks = not port_tack.empty and not starboard_tack.empty
        
        if not has_both_tacks:
            logger.warning("Missing one tack, cannot estimate wind direction reliably")
            return WindEstimate(
                direction=initial_direction,
                confidence="low", 
                user_provided=True,
                method="basic",
                port_angle=None if port_tack.empty else port_tack['angle_to_wind'].mean(),
                starboard_angle=None if starboard_tack.empty else starboard_tack['angle_to_wind'].mean(),
                port_count=len(port_tack),
                starboard_count=len(starboard_tack),
                iteration_count=0,
                has_both_tacks=has_both_tacks
            )
        
        # Calculate average angles
        port_avg_angle = port_tack['angle_to_wind'].mean()
        starboard_avg_angle = starboard_tack['angle_to_wind'].mean()
        
        # Calculate difference between tacks
        tack_difference = abs(port_avg_angle - starboard_avg_angle)
        
        # Calculate average wind direction
        avg_angle = (port_avg_angle + starboard_avg_angle) / 2
        
        # Determine confidence based on tack difference
        if tack_difference < 10:
            confidence = "high"
        elif tack_difference < 20:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Compute the refined wind direction
        # If the difference between tacks is too large, use the initial wind direction
        if tack_difference > 30:
            logger.warning(f"Tack difference too large ({tack_difference:.1f}°), using initial wind direction")
            refined_wind = initial_direction
        else:
            # Current + adjustment based on average angle
            refined_wind = initial_direction
        
        return WindEstimate(
            direction=refined_wind,
            confidence=confidence,
            user_provided=False,
            method="basic",
            port_angle=port_avg_angle,
            starboard_angle=starboard_avg_angle,
            port_count=len(port_tack),
            starboard_count=len(starboard_tack),
            iteration_count=0,
            tack_difference=tack_difference,
            has_both_tacks=has_both_tacks
        )


class IterativeStrategy:
    """
    Iterative wind direction estimation strategy.
    
    This strategy iteratively refines the wind direction estimate by
    analyzing the difference between port and starboard tack angles.
    """
    
    def estimate(
        self, 
        segments: pd.DataFrame,
        initial_direction: float,
        suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        convergence_threshold: float = DEFAULT_CONVERGENCE_THRESHOLD,
        **kwargs
    ) -> WindEstimate:
        """
        Estimate wind direction using iterative refinement.
        
        Args:
            segments: DataFrame with segments
            initial_direction: Initial wind direction estimate
            suspicious_angle_threshold: Threshold for suspicious angles
            max_iterations: Maximum number of iterations
            convergence_threshold: Convergence threshold in degrees
            **kwargs: Additional keyword arguments
            
        Returns:
            WindEstimate: Estimated wind direction
        """
        from core.segments import analyze_wind_angles
        
        # Initialize
        current_wind = initial_direction
        iteration_count = 0
        converged = False
        
        # Keep track of the adjustment history
        adjustments = []
        
        # Iterative refinement
        while iteration_count < max_iterations and not converged:
            # Analyze with current wind direction
            df = analyze_wind_angles(segments.copy(), current_wind)
            
            # Filter out suspicious segments
            df = df[df['angle_to_wind'] >= suspicious_angle_threshold]
            
            # Split by tack
            port_tack = df[df['tack'] == 'Port']
            starboard_tack = df[df['tack'] == 'Starboard']
            
            # Check if we have both tacks
            has_both_tacks = not port_tack.empty and not starboard_tack.empty
            
            if not has_both_tacks:
                logger.warning("Missing one tack, cannot estimate wind direction reliably")
                break
            
            # Calculate average angles
            port_avg_angle = port_tack['angle_to_wind'].mean()
            starboard_avg_angle = starboard_tack['angle_to_wind'].mean()
            
            # Calculate difference between tacks
            tack_difference = abs(port_avg_angle - starboard_avg_angle)
            
            # Calculate adjustment
            # If port angle is smaller than starboard, wind is more from port side
            adjustment = (port_avg_angle - starboard_avg_angle) / 2
            adjustments.append(adjustment)
            
            # Check for convergence
            if abs(adjustment) < convergence_threshold:
                converged = True
                logger.info(f"Wind direction estimation converged after {iteration_count+1} iterations")
            
            # Apply adjustment
            new_wind = (current_wind + adjustment) % 360
            
            # Update for next iteration
            current_wind = new_wind
            iteration_count += 1
        
        # Determine confidence based on convergence and tack difference
        confidence = "low"
        if converged:
            if tack_difference < 10:
                confidence = "high"
            elif tack_difference < 20:
                confidence = "medium"
        
        # Only consider the estimate valid if we have both tacks and either converged or did max iterations
        user_provided = not has_both_tacks
        
        port_avg_angle = port_tack['angle_to_wind'].mean() if not port_tack.empty else None
        starboard_avg_angle = starboard_tack['angle_to_wind'].mean() if not starboard_tack.empty else None
        
        return WindEstimate(
            direction=current_wind,
            confidence=confidence,
            user_provided=user_provided,
            method="iterative",
            port_angle=port_avg_angle,
            starboard_angle=starboard_avg_angle,
            port_count=len(port_tack) if not port_tack.empty else 0,
            starboard_count=len(starboard_tack) if not starboard_tack.empty else 0,
            iteration_count=iteration_count,
            tack_difference=tack_difference if has_both_tacks else None,
            has_both_tacks=has_both_tacks,
            adjustments=adjustments
        )


class WeightedStrategy:
    """
    Weighted wind direction estimation strategy.
    
    This strategy uses segment distance weighting to give more importance
    to longer segments when estimating wind direction.
    """
    
    def estimate(
        self, 
        segments: pd.DataFrame,
        initial_direction: float,
        suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
        min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE,
        **kwargs
    ) -> WindEstimate:
        """
        Estimate wind direction using distance-weighted segments.
        
        Args:
            segments: DataFrame with segments
            initial_direction: Initial wind direction estimate
            suspicious_angle_threshold: Threshold for suspicious angles
            min_segment_distance: Minimum segment distance to consider
            **kwargs: Additional keyword arguments
            
        Returns:
            WindEstimate: Estimated wind direction
        """
        # Make a copy to avoid modifying the original
        df = segments.copy()
        
        # Filter to include only segments that meet criteria
        df = df[df['angle_to_wind'] >= suspicious_angle_threshold]
        df = df[df['distance'] >= min_segment_distance]
        
        # Log our filtering
        filtered_count = len(segments) - len(df)
        if filtered_count > 0:
            suspicious_count = len(segments[segments['angle_to_wind'] < suspicious_angle_threshold])
            distance_count = len(segments[segments['distance'] < min_segment_distance])
            logger.info(f"Filtered out {filtered_count} segments out of {len(segments)}")
            logger.info(f"Suspicious reasons: {{'Angle to wind < {suspicious_angle_threshold}°': {suspicious_count}, 'Distance < {min_segment_distance}m': {distance_count}}}")
        
        logger.info(f"Filtered to {len(df)} segments with distance >= {min_segment_distance}m")
        
        # Split by tack
        port_tack = df[df['tack'] == 'Port']
        starboard_tack = df[df['tack'] == 'Starboard']
        
        # Check if we have both tacks
        has_both_tacks = not port_tack.empty and not starboard_tack.empty
        port_count = len(port_tack)
        starboard_count = len(starboard_tack)
        
        if not has_both_tacks:
            logger.warning("Missing one tack, cannot estimate wind direction reliably")
            return WindEstimate(
                direction=initial_direction,
                confidence="low", 
                user_provided=True,
                method="weighted",
                port_angle=None if port_tack.empty else port_tack['angle_to_wind'].mean(),
                starboard_angle=None if starboard_tack.empty else starboard_tack['angle_to_wind'].mean(),
                port_count=port_count,
                starboard_count=starboard_count,
                has_both_tacks=has_both_tacks
            )
        
        # Calculate weighted averages using distance as weight
        port_weighted_avg = np.average(
            port_tack['angle_to_wind'], 
            weights=port_tack['distance']
        ) if not port_tack.empty else None
        
        starboard_weighted_avg = np.average(
            starboard_tack['angle_to_wind'], 
            weights=starboard_tack['distance']
        ) if not starboard_tack.empty else None
        
        logger.info(f"Port tack weighted average angle: {port_weighted_avg:.1f}° (from {port_count} segments)")
        logger.info(f"Starboard tack weighted average angle: {starboard_weighted_avg:.1f}° (from {starboard_count} segments)")
        
        # Calculate the tack difference
        tack_difference = abs(port_weighted_avg - starboard_weighted_avg)
        
        # Determine confidence based on tack difference and number of segments
        if tack_difference < 10 and port_count >= 3 and starboard_count >= 3:
            confidence = "high"
        elif tack_difference < 20 and port_count >= 2 and starboard_count >= 2:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Calculate wind adjustment based on tack difference
        # If port angle is larger than starboard, we need to reduce the wind angle
        adjustment = (port_weighted_avg - starboard_weighted_avg) / 2
        
        # Apply adjustment to initial wind direction
        refined_wind = (initial_direction - adjustment) % 360
        
        logger.info(f"Estimated wind: {refined_wind:.1f}° (adjustment: {-adjustment:.1f}°)")
        
        return WindEstimate(
            direction=refined_wind,
            confidence=confidence,
            user_provided=False,
            method="weighted",
            port_angle=port_weighted_avg,
            starboard_angle=starboard_weighted_avg,
            port_count=port_count,
            starboard_count=starboard_count,
            tack_difference=tack_difference,
            has_both_tacks=has_both_tacks
        )


class WindEstimator:
    """
    Unified wind direction estimator.
    
    This class provides a consistent interface for different wind estimation
    strategies, making it easy to switch between them or combine their results.
    """
    
    def __init__(self):
        """Initialize the estimator with available strategies."""
        self.strategies: Dict[str, EstimationStrategy] = {
            "basic": BasicStrategy(),
            "iterative": IterativeStrategy(),
            "weighted": WeightedStrategy()
        }
    
    def estimate(
        self, 
        segments: pd.DataFrame,
        initial_direction: float = DEFAULT_WIND_DIRECTION,
        method: str = "weighted",
        **kwargs
    ) -> WindEstimate:
        """
        Estimate wind direction using the specified method.
        
        Args:
            segments: DataFrame with segments
            initial_direction: Initial wind direction estimate
            method: Estimation method ("weighted", "iterative", or "basic")
            **kwargs: Additional parameters for the estimation strategy
            
        Returns:
            WindEstimate: Estimated wind direction
            
        Raises:
            ValueError: If the specified method is not supported
        """
        if method not in self.strategies:
            raise ValueError(f"Unsupported estimation method: {method}")
        
        strategy = self.strategies[method]
        return strategy.estimate(segments, initial_direction, **kwargs)
    
    def estimate_all(
        self, 
        segments: pd.DataFrame,
        initial_direction: float = DEFAULT_WIND_DIRECTION,
        **kwargs
    ) -> Dict[str, WindEstimate]:
        """
        Estimate wind direction using all available methods.
        
        Args:
            segments: DataFrame with segments
            initial_direction: Initial wind direction estimate
            **kwargs: Additional parameters for the estimation strategies
            
        Returns:
            Dict[str, WindEstimate]: Mapping of method names to their estimates
        """
        results = {}
        for method, strategy in self.strategies.items():
            results[method] = strategy.estimate(segments, initial_direction, **kwargs)
        return results