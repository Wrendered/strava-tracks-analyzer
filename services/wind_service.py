"""
Wind analysis service.

This module provides business logic for wind direction estimation and VMG calculations,
used by the API backend.
"""

import pandas as pd
import numpy as np
import logging
import math
from typing import Optional
from dataclasses import dataclass

from core.wind.factory import estimate_wind_direction_factory, WindEstimationParams
from core.wind.models import WindEstimate
from core.metrics_advanced import (
    calculate_vmg_upwind,
    calculate_vmg_downwind
)
from config.settings import (
    DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD,
    DEFAULT_WIND_DIRECTION
)

# Advanced algorithm configuration
DEFAULT_MIN_SEGMENT_DISTANCE = 50  # Minimum segment distance for algorithms in meters
DEFAULT_VMG_ANGLE_RANGE = 20       # Range around best angle to include for VMG calculation

logger = logging.getLogger(__name__)


@dataclass
class WindAnalysisParams:
    """Parameters for wind analysis."""
    initial_wind_direction: float = DEFAULT_WIND_DIRECTION
    suspicious_angle_threshold: float = DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD
    min_segment_distance: float = DEFAULT_MIN_SEGMENT_DISTANCE
    vmg_angle_range: float = DEFAULT_VMG_ANGLE_RANGE


class WindService:
    """
    Service for wind analysis and related calculations.

    This class centralizes the business logic for wind direction estimation,
    VMG calculations, and other wind-related functionality.
    """

    def estimate_wind_direction(
        self,
        segments: pd.DataFrame,
        params: Optional[WindAnalysisParams] = None,
        method: str = "iterative"
    ) -> WindEstimate:
        """
        Estimate wind direction from segments using the specified method.

        Args:
            segments: DataFrame with segments
            params: Parameters for wind analysis, or None to use defaults
            method: Estimation method ("iterative", "weighted", or "basic")

        Returns:
            WindEstimate: Object with estimated wind direction and confidence
        """
        if params is None:
            params = WindAnalysisParams()

        # Use factory pattern for wind estimation
        wind_params = WindEstimationParams(
            suspicious_angle_threshold=params.suspicious_angle_threshold,
            min_segment_distance=params.min_segment_distance
        )

        result = estimate_wind_direction_factory(
            segments.copy(),
            initial_wind=params.initial_wind_direction,
            method=method,
            params=wind_params
        )

        return result

    @staticmethod
    def calculate_vmg_upwind(
        upwind_segments: pd.DataFrame,
        params: Optional[WindAnalysisParams] = None
    ) -> Optional[float]:
        """
        Calculate VMG (velocity made good) upwind.

        Args:
            upwind_segments: DataFrame with upwind segments
            params: Parameters for VMG calculation, or None to use defaults

        Returns:
            float: VMG upwind in knots, or None if calculation failed
        """
        if params is None:
            params = WindAnalysisParams()

        return calculate_vmg_upwind(
            upwind_segments,
            angle_range=params.vmg_angle_range,
            min_segment_distance=params.min_segment_distance
        )

    @staticmethod
    def calculate_vmg_downwind(
        downwind_segments: pd.DataFrame,
        params: Optional[WindAnalysisParams] = None
    ) -> Optional[float]:
        """
        Calculate VMG (velocity made good) downwind.

        Args:
            downwind_segments: DataFrame with downwind segments
            params: Parameters for VMG calculation, or None to use defaults

        Returns:
            float: VMG downwind in knots, or None if calculation failed
        """
        if params is None:
            params = WindAnalysisParams()

        return calculate_vmg_downwind(
            downwind_segments,
            angle_range=params.vmg_angle_range,
            min_segment_distance=params.min_segment_distance
        )

    @staticmethod
    def calculate_fallback_vmg_upwind(best_port: pd.Series, best_starboard: pd.Series) -> float:
        """
        Calculate a fallback VMG upwind when advanced algorithm cannot be used.

        Args:
            best_port: Best port tack segment
            best_starboard: Best starboard tack segment

        Returns:
            float: Fallback VMG upwind in knots
        """
        pointing_power = (best_port['angle_to_wind'] + best_starboard['angle_to_wind']) / 2
        avg_upwind_speed = (best_port['speed'] + best_starboard['speed']) / 2
        return avg_upwind_speed * math.cos(math.radians(pointing_power))


def get_wind_service() -> WindService:
    """
    Get a WindService instance.

    Returns:
        WindService instance
    """
    return WindService()
