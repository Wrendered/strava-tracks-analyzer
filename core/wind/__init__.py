"""
Wind estimation module.

This module provides all wind direction estimation functionality with clean,
organized interfaces. All algorithms have been consolidated for maintainability.
"""

# Import models first (no dependencies)
from .models import WindEstimate

# Lazy import algorithms to avoid circular imports
# Users should import directly: from core.wind.algorithms import estimate_wind_direction_iterative

__all__ = [
    'WindEstimate'
]