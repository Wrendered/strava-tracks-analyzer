"""
Wind models and data structures.

This module contains models and data structures for working with wind data.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
import numpy as np
import pandas as pd

@dataclass
class WindEstimate:
    """Wind direction estimate with confidence information."""
    direction: float
    confidence: str  # "high", "medium", "low", "none"
    port_angle: Optional[float] = None
    starboard_angle: Optional[float] = None
    port_count: int = 0
    starboard_count: int = 0
    user_provided: bool = False
    
    def __post_init__(self):
        # Normalize direction to 0-359 range
        self.direction = self.direction % 360
    
    @property
    def has_both_tacks(self) -> bool:
        """Check if we have data from both tacks."""
        return self.port_angle is not None and self.starboard_angle is not None
    
    @property
    def tack_difference(self) -> Optional[float]:
        """Get the difference between port and starboard angles."""
        if self.has_both_tacks and self.port_angle is not None and self.starboard_angle is not None:
            return abs(self.port_angle - self.starboard_angle)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'direction': round(self.direction, 1),
            'confidence': self.confidence,
            'port_angle': round(self.port_angle, 1) if self.port_angle is not None else None,
            'starboard_angle': round(self.starboard_angle, 1) if self.starboard_angle is not None else None,
            'port_count': self.port_count,
            'starboard_count': self.starboard_count,
            'user_provided': self.user_provided,
            'has_both_tacks': self.has_both_tacks,
            'tack_difference': round(self.tack_difference, 1) if self.tack_difference is not None else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindEstimate':
        """Create WindEstimate from dictionary."""
        return cls(
            direction=data['direction'],
            confidence=data['confidence'],
            port_angle=data.get('port_angle'),
            starboard_angle=data.get('starboard_angle'),
            port_count=data.get('port_count', 0),
            starboard_count=data.get('starboard_count', 0),
            user_provided=data.get('user_provided', False)
        )
    
    @classmethod
    def from_user_input(cls, direction: float) -> 'WindEstimate':
        """Create WindEstimate from user input."""
        return cls(
            direction=direction,
            confidence="none",
            user_provided=True
        )

def determine_confidence_level(stretches: pd.DataFrame) -> str:
    """
    Determine the confidence level in the wind direction estimate based on the data quality.
    
    Args:
        stretches: DataFrame with sailing segments
        
    Returns:
        str: Confidence level ("high", "medium", "low", "none")
    """
    if stretches.empty:
        return "none"
    
    # Split by tack
    port_tack = stretches[stretches['tack'] == 'Port']
    starboard_tack = stretches[stretches['tack'] == 'Starboard']
    
    # Get upwind segments
    upwind = stretches[stretches['angle_to_wind'] < 90]
    port_upwind = upwind[upwind['tack'] == 'Port']
    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
    
    # Check both tacks present
    has_both_tacks = len(port_tack) > 0 and len(starboard_tack) > 0
    has_both_upwind = len(port_upwind) > 0 and len(starboard_upwind) > 0
    
    # Calculate segment counts
    total_segments = len(stretches)
    upwind_segments = len(upwind)
    
    # Calculate angle consistency (standard deviation)
    port_std = port_upwind['angle_to_wind'].std() if len(port_upwind) > 2 else float('inf')
    starboard_std = starboard_upwind['angle_to_wind'].std() if len(starboard_upwind) > 2 else float('inf')
    
    # Determine confidence level
    if has_both_upwind and total_segments >= 10 and upwind_segments >= 5:
        if port_std < 10 and starboard_std < 10:
            return "high"
        elif port_std < 15 and starboard_std < 15:
            return "medium"
        else:
            return "low"
    elif has_both_tacks and upwind_segments >= 3:
        return "medium"
    elif upwind_segments >= 2:
        return "low"
    else:
        return "none"