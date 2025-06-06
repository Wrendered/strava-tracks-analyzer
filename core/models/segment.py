"""
Segment data models.

This module defines the data structures for sailing segments detected in GPS tracks.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd


@dataclass
class Segment:
    """
    Represents a consistent sailing segment.
    
    A segment is a portion of a track where the sailing angle (bearing) 
    remains consistent within a specified tolerance.
    """
    # Time boundaries
    start_time: datetime
    end_time: datetime
    
    # Index boundaries in the original data
    start_idx: int
    end_idx: int
    
    # Sailing characteristics
    bearing: float  # Average bearing in degrees (0-360)
    distance: float  # Total distance in meters
    duration: float  # Total duration in seconds
    avg_speed_knots: float  # Average speed in knots
    point_count: int  # Number of GPS points in this segment
    
    # Optional wind analysis (added later)
    angle_to_wind: Optional[float] = None  # Angle to wind in degrees (0-180)
    tack: Optional[str] = None  # 'Port' or 'Starboard'
    direction: Optional[str] = None  # 'Upwind' or 'Downwind'
    
    # Quality metrics (optional)
    quality_score: Optional[float] = None  # 0-1 quality score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary for DataFrame creation."""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'bearing': self.bearing,
            'distance': self.distance,
            'duration': self.duration,
            'avg_speed_knots': self.avg_speed_knots,
            'point_count': self.point_count,
            'angle_to_wind': self.angle_to_wind,
            'tack': self.tack,
            'direction': self.direction,
            'quality_score': self.quality_score
        }
    
    @property
    def avg_speed_ms(self) -> float:
        """Average speed in meters per second."""
        from core.constants import KNOTS_TO_METERS_PER_SECOND
        return self.avg_speed_knots * KNOTS_TO_METERS_PER_SECOND
    
    @property
    def distance_km(self) -> float:
        """Distance in kilometers."""
        return self.distance / 1000.0
    
    @property
    def duration_minutes(self) -> float:
        """Duration in minutes."""
        return self.duration / 60.0


def segments_to_dataframe(segments: List[Segment]) -> pd.DataFrame:
    """
    Convert a list of segments to a pandas DataFrame.
    
    Args:
        segments: List of Segment objects
        
    Returns:
        pandas DataFrame with segment data
    """
    if not segments:
        return pd.DataFrame()
    
    data = [segment.to_dict() for segment in segments]
    return pd.DataFrame(data)


def dataframe_to_segments(df: pd.DataFrame) -> List[Segment]:
    """
    Convert a pandas DataFrame to a list of Segment objects.
    
    Args:
        df: DataFrame with segment columns
        
    Returns:
        List of Segment objects
    """
    segments = []
    
    for _, row in df.iterrows():
        segment = Segment(
            start_time=row['start_time'],
            end_time=row['end_time'],
            start_idx=row['start_idx'],
            end_idx=row['end_idx'],
            bearing=row['bearing'],
            distance=row['distance'],
            duration=row['duration'],
            avg_speed_knots=row['avg_speed_knots'],
            point_count=row['point_count'],
            angle_to_wind=row.get('angle_to_wind'),
            tack=row.get('tack'),
            direction=row.get('direction'),
            quality_score=row.get('quality_score')
        )
        segments.append(segment)
    
    return segments