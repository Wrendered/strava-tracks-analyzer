"""
Track data models.

This module defines the core data structures for track analysis,
providing type safety and encapsulation of track-related data.
"""

import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any

@dataclass
class TrackPoint:
    """
    Single point in a GPS track.
    """
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    time: Optional[datetime] = None
    speed: Optional[float] = None  # in m/s
    bearing: Optional[float] = None  # in degrees
    distance: Optional[float] = None  # distance from previous point in meters
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackPoint':
        """Create a TrackPoint from a dictionary."""
        return cls(
            latitude=data['latitude'],
            longitude=data['longitude'],
            elevation=data.get('elevation'),
            time=data.get('time'),
            speed=data.get('speed'),
            bearing=data.get('bearing'),
            distance=data.get('distance')
        )
    
    @property
    def speed_knots(self) -> Optional[float]:
        """Get speed in knots."""
        if self.speed is None:
            return None
        return self.speed * 1.94384  # m/s to knots


@dataclass
class TrackSegment:
    """
    A segment of a track with consistent properties.
    """
    start_idx: int
    end_idx: int
    bearing: float  # in degrees
    distance: float  # in meters
    duration: float  # in seconds
    speed: float  # in knots
    points: List[TrackPoint] = field(default_factory=list)
    
    # Additional properties from wind analysis
    wind_direction: Optional[float] = None
    angle_to_wind: Optional[float] = None
    tack: Optional[str] = None  # 'Port' or 'Starboard'
    sailing_type: Optional[str] = None  # e.g., 'Upwind Port'
    upwind_downwind: Optional[str] = None  # 'Upwind' or 'Downwind'
    suspicious: bool = False
    quality_score: Optional[float] = None
    
    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> 'TrackSegment':
        """Create a TrackSegment from a DataFrame row."""
        segment = cls(
            start_idx=row['start_idx'],
            end_idx=row['end_idx'],
            bearing=row['bearing'],
            distance=row['distance'],
            duration=row['duration'],
            speed=row['speed']
        )
        
        # Add wind analysis properties if available
        if 'wind_direction' in row:
            segment.wind_direction = row['wind_direction']
        if 'angle_to_wind' in row:
            segment.angle_to_wind = row['angle_to_wind']
        if 'tack' in row:
            segment.tack = row['tack']
        if 'sailing_type' in row:
            segment.sailing_type = row['sailing_type']
        if 'upwind_downwind' in row:
            segment.upwind_downwind = row['upwind_downwind']
        if 'suspicious' in row:
            segment.suspicious = row['suspicious']
        if 'quality_score' in row:
            segment.quality_score = row['quality_score']
        
        return segment
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary."""
        result = {
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'bearing': self.bearing,
            'distance': self.distance,
            'duration': self.duration,
            'speed': self.speed
        }
        
        # Add wind analysis properties if available
        if self.wind_direction is not None:
            result['wind_direction'] = self.wind_direction
        if self.angle_to_wind is not None:
            result['angle_to_wind'] = self.angle_to_wind
        if self.tack is not None:
            result['tack'] = self.tack
        if self.sailing_type is not None:
            result['sailing_type'] = self.sailing_type
        if self.upwind_downwind is not None:
            result['upwind_downwind'] = self.upwind_downwind
        result['suspicious'] = self.suspicious
        if self.quality_score is not None:
            result['quality_score'] = self.quality_score
        
        return result
    
    @property
    def is_upwind(self) -> bool:
        """Check if this is an upwind segment."""
        if self.angle_to_wind is None:
            return False
        return self.angle_to_wind < 90
    
    @property
    def is_port_tack(self) -> bool:
        """Check if this is a port tack segment."""
        return self.tack == 'Port'
    
    @property
    def vmg(self) -> Optional[float]:
        """Calculate velocity made good."""
        import math
        if self.angle_to_wind is None:
            return None
        
        # Use speed * cos(angle) for upwind, speed * -cos(angle) for downwind
        angle_rad = math.radians(self.angle_to_wind)
        if self.is_upwind:
            return self.speed * math.cos(angle_rad)
        else:
            angle_from_downwind = abs(180 - self.angle_to_wind)
            return self.speed * math.cos(math.radians(angle_from_downwind))


@dataclass
class Track:
    """
    Complete GPS track with derived metrics.
    """
    name: str
    points: List[TrackPoint]
    segments: List[TrackSegment] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def dataframe(self) -> pd.DataFrame:
        """Convert track points to DataFrame."""
        data = []
        for point in self.points:
            data.append({
                'latitude': point.latitude,
                'longitude': point.longitude,
                'elevation': point.elevation,
                'time': point.time,
                'speed': point.speed,
                'bearing': point.bearing,
                'distance': point.distance
            })
        return pd.DataFrame(data)
    
    @property
    def segments_dataframe(self) -> pd.DataFrame:
        """Convert segments to DataFrame."""
        data = []
        for segment in self.segments:
            data.append(segment.to_dict())
        return pd.DataFrame(data)
    
    @classmethod
    def from_dataframes(cls, name: str, points_df: pd.DataFrame, segments_df: Optional[pd.DataFrame] = None) -> 'Track':
        """Create a Track from DataFrames."""
        # Convert points DataFrame to TrackPoint objects
        points = []
        for _, row in points_df.iterrows():
            points.append(TrackPoint.from_dict(row))
        
        # Create Track object
        track = cls(name=name, points=points)
        
        # Add segments if provided
        if segments_df is not None:
            segments = []
            for _, row in segments_df.iterrows():
                segments.append(TrackSegment.from_dataframe_row(row))
            track.segments = segments
        
        return track
    
    def get_upwind_segments(self) -> List[TrackSegment]:
        """Get all upwind segments."""
        return [segment for segment in self.segments if segment.is_upwind]
    
    def get_downwind_segments(self) -> List[TrackSegment]:
        """Get all downwind segments."""
        return [segment for segment in self.segments if not segment.is_upwind]
    
    def get_port_tack_segments(self) -> List[TrackSegment]:
        """Get all port tack segments."""
        return [segment for segment in self.segments if segment.is_port_tack]
    
    def get_starboard_tack_segments(self) -> List[TrackSegment]:
        """Get all starboard tack segments."""
        return [segment for segment in self.segments if not segment.is_port_tack]
    
    def get_non_suspicious_segments(self) -> List[TrackSegment]:
        """Get all non-suspicious segments."""
        return [segment for segment in self.segments if not segment.suspicious]