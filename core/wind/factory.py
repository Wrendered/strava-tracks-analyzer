"""
Wind estimation algorithm factory and base classes.

This module provides a factory pattern for wind estimation algorithms.
Currently supports 'iterative' (recommended) and 'weighted' (legacy) methods.
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Type, Optional
from dataclasses import dataclass

from core.wind.models import WindEstimate
from core.constants import (
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_MIN_SEGMENT_DISTANCE_METERS
)


@dataclass
class WindEstimationParams:
    """Parameters for wind estimation algorithms."""
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE_METERS
    max_iterations: int = 5

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for function calls."""
        return {
            'suspicious_angle_threshold': self.suspicious_angle_threshold,
            'min_segment_distance': self.min_segment_distance,
            'max_iterations': self.max_iterations
        }


class WindEstimator(ABC):
    """Abstract base class for wind estimation algorithms."""

    @abstractmethod
    def estimate(
        self,
        segments: pd.DataFrame,
        initial_wind: float,
        params: Optional[WindEstimationParams] = None
    ) -> WindEstimate:
        """
        Estimate wind direction from sailing segments.

        Args:
            segments: DataFrame with sailing segments
            initial_wind: Initial wind direction estimate
            params: Optional parameters for estimation

        Returns:
            WindEstimate with direction and confidence
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the algorithm."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the algorithm."""
        pass


class IterativeWindEstimator(WindEstimator):
    """
    Iterative wind estimation with proper tack reclassification.

    This is the recommended algorithm. It:
    - Reclassifies port/starboard tacks on each iteration
    - Uses median angles for outlier resistance
    - Uses distance weighting for better accuracy
    - Converges to balanced port/starboard angles
    """

    def estimate(
        self,
        segments: pd.DataFrame,
        initial_wind: float,
        params: Optional[WindEstimationParams] = None
    ) -> WindEstimate:
        """Estimate wind using iterative algorithm."""
        if params is None:
            params = WindEstimationParams()

        from core.wind.algorithms import estimate_wind_direction_iterative

        return estimate_wind_direction_iterative(
            segments=segments,
            initial_wind=initial_wind,
            suspicious_angle_threshold=params.suspicious_angle_threshold,
            min_segment_distance=params.min_segment_distance,
            max_iterations=params.max_iterations
        )

    @property
    def name(self) -> str:
        return "Iterative"

    @property
    def description(self) -> str:
        return "Advanced algorithm with iterative tack reclassification for accurate wind estimation"


class WeightedWindEstimator(WindEstimator):
    """
    Distance-weighted wind estimation (legacy algorithm).

    Note: This algorithm has a known limitation - it doesn't reclassify
    tacks after adjusting wind direction. Use 'iterative' for better results.
    """

    def estimate(
        self,
        segments: pd.DataFrame,
        initial_wind: float,
        params: Optional[WindEstimationParams] = None
    ) -> WindEstimate:
        """Estimate wind using weighted algorithm."""
        if params is None:
            params = WindEstimationParams()

        from core.wind.algorithms import estimate_wind_direction_weighted

        return estimate_wind_direction_weighted(
            stretches=segments,
            user_wind_direction=initial_wind,
            suspicious_angle_threshold=params.suspicious_angle_threshold,
            min_segment_distance=params.min_segment_distance
        )

    @property
    def name(self) -> str:
        return "Weighted"

    @property
    def description(self) -> str:
        return "Legacy distance-weighted algorithm (has known tack classification limitation)"


class WindEstimationFactory:
    """Factory for creating wind estimation algorithms."""

    _estimators: Dict[str, Type[WindEstimator]] = {
        'iterative': IterativeWindEstimator,
        'weighted': WeightedWindEstimator,
    }

    @classmethod
    def create_estimator(cls, method: str) -> WindEstimator:
        """
        Create a wind estimator for the specified method.

        Args:
            method: Algorithm method ('iterative' or 'weighted')

        Returns:
            WindEstimator instance

        Raises:
            ValueError: If method is not supported
        """
        method_lower = method.lower()

        # Default to iterative for unknown methods
        if method_lower not in cls._estimators:
            method_lower = 'iterative'

        return cls._estimators[method_lower]()

    @classmethod
    def get_available_methods(cls) -> Dict[str, str]:
        """Get available estimation methods with descriptions."""
        result = {}
        for method_name, estimator_class in cls._estimators.items():
            estimator = estimator_class()
            result[method_name] = f"{estimator.name}: {estimator.description}"
        return result

    @classmethod
    def get_default_method(cls) -> str:
        """Get the recommended default method."""
        return 'iterative'


def estimate_wind_direction_factory(
    segments: pd.DataFrame,
    initial_wind: float,
    method: str = 'iterative',
    params: Optional[WindEstimationParams] = None
) -> WindEstimate:
    """
    Convenience function to estimate wind direction using any algorithm.

    Args:
        segments: DataFrame with sailing segments
        initial_wind: Initial wind direction estimate
        method: Algorithm to use ('iterative' or 'weighted', defaults to 'iterative')
        params: Optional parameters

    Returns:
        WindEstimate with direction and confidence
    """
    estimator = WindEstimationFactory.create_estimator(method)
    return estimator.estimate(segments, initial_wind, params)
