"""Model for gear comparison items.

This module contains the GearItem class for representing gear setups for comparison.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import pandas as pd
import json
import uuid
from datetime import datetime

from core.metrics_advanced import calculate_vmg_upwind, calculate_vmg_downwind

@dataclass
class GearItem:
    """Class representing a gear setup for comparison."""
    id: str  # Unique identifier for the gear item
    title: str  # User-provided title for the gear setup
    date: Optional[str] = None  # Date of the session
    
    # Track metrics
    track_name: Optional[str] = None  # Name of the track
    wind_direction: Optional[float] = None  # Wind direction in degrees
    avg_speed: Optional[float] = None  # Average speed in knots
    max_speed: Optional[float] = None  # Maximum speed in knots
    distance: Optional[float] = None  # Total distance in km
    duration: Optional[float] = None  # Duration in minutes
    active_duration: Optional[float] = None  # Active duration in minutes
    
    # Performance metrics
    upwind_progress_speed: Optional[float] = None  # Legacy field - kept for backward compatibility
    vmg_upwind: Optional[float] = None  # Velocity Made Good upwind in knots
    best_port_upwind_angle: Optional[float] = None  # Best port upwind angle in degrees
    best_port_upwind_speed: Optional[float] = None  # Best port upwind speed in knots
    best_starboard_upwind_angle: Optional[float] = None  # Best starboard upwind angle in degrees
    best_starboard_upwind_speed: Optional[float] = None  # Best starboard upwind speed in knots
    best_port_downwind_angle: Optional[float] = None  # Best port downwind angle in degrees
    best_port_downwind_speed: Optional[float] = None  # Best port downwind speed in knots
    best_starboard_downwind_angle: Optional[float] = None  # Best starboard downwind angle in degrees
    best_starboard_downwind_speed: Optional[float] = None  # Best starboard downwind speed in knots
    avg_upwind_angle: Optional[float] = None  # Average upwind angle in degrees
    avg_port_tack_angle: Optional[float] = None  # Average port tack angle in degrees
    avg_starboard_tack_angle: Optional[float] = None  # Average starboard tack angle in degrees
    port_starboard_diff: Optional[float] = None  # Difference between port and starboard angles
    
    # Source data info
    source_file: Optional[str] = None  # Original source filename
    timestamp: Optional[str] = field(default_factory=lambda: datetime.now().isoformat())  # When the item was created
    
    @classmethod
    def from_session_state(cls, title: str, session_state: Dict[str, Any]) -> "GearItem":
        """Create a GearItem from session state data.
        
        Args:
            title: User-provided title for the gear setup
            session_state: Streamlit session state containing track data
            
        Returns:
            GearItem: New GearItem instance with data from session state
        """
        # Get metrics from session state
        metrics = session_state.get('track_metrics', {})
        
        # Extract performance metrics from track stretches if available
        upwind_progress = None  # Legacy field
        vmg_upwind = None  # New field
        best_port_upwind = {"angle": None, "speed": None}
        best_starboard_upwind = {"angle": None, "speed": None}
        best_port_downwind = {"angle": None, "speed": None}
        best_starboard_downwind = {"angle": None, "speed": None}
        
        if 'track_stretches' in session_state and session_state['track_stretches'] is not None:
            stretches = session_state['track_stretches']
            
            # Split into upwind/downwind for analysis
            # IMPORTANT: Speeds in stretches DataFrame are already in knots
            # They were converted from m/s in core/segments.py
            if not stretches.empty:
                # Use same method as main page and bulk upload: check 'direction' column
                upwind = stretches[stretches.get('direction', '').str.lower() == 'upwind'] if 'direction' in stretches.columns else pd.DataFrame()
                downwind = stretches[stretches.get('direction', '').str.lower() == 'downwind'] if 'direction' in stretches.columns else pd.DataFrame()
                
                # Reset best tack variables for recalculation
                best_port_upwind = {"angle": None, "speed": None}
                best_starboard_upwind = {"angle": None, "speed": None}
                
                # Get upwind metrics
                if not upwind.empty:
                    port_upwind = upwind[upwind['tack'] == 'Port']
                    starboard_upwind = upwind[upwind['tack'] == 'Starboard']
                    
                    # Find best port tack upwind angle
                    if not port_upwind.empty and len(port_upwind) > 0:
                        best_port = port_upwind.loc[port_upwind['angle_to_wind'].idxmin()]
                        best_port_upwind = {
                            "angle": best_port['angle_to_wind'],
                            "speed": best_port['avg_speed_knots']  # Speed is already in knots in the UI
                        }
                    
                    # Find best starboard tack upwind angle
                    if not starboard_upwind.empty and len(starboard_upwind) > 0:
                        best_starboard = starboard_upwind.loc[starboard_upwind['angle_to_wind'].idxmin()]
                        best_starboard_upwind = {
                            "angle": best_starboard['angle_to_wind'],
                            "speed": best_starboard['avg_speed_knots']  # Speed is already in knots in the UI
                        }
                    
                    # Calculate VMG using the standard algorithm
                    if not upwind.empty:
                        vmg_upwind = calculate_vmg_upwind(upwind)
                    
                    # Calculate upwind progress speed (legacy field) when we have both tacks
                    if (best_port_upwind["angle"] is not None and best_port_upwind["speed"] is not None and 
                        best_starboard_upwind["angle"] is not None and best_starboard_upwind["speed"] is not None):
                        import math
                        # Simply average the angles
                        pointing_power = (best_port_upwind["angle"] + best_starboard_upwind["angle"]) / 2
                        
                        # Average speed
                        avg_upwind_speed = (best_port_upwind["speed"] + best_starboard_upwind["speed"]) / 2
                        
                        # Calculate upwind progress speed (legacy field)
                        upwind_progress = avg_upwind_speed * math.cos(math.radians(pointing_power))
                
                # Get downwind metrics
                if not downwind.empty:
                    port_downwind = downwind[downwind['tack'] == 'Port']
                    starboard_downwind = downwind[downwind['tack'] == 'Starboard']
                    
                    # Find best port tack downwind angle
                    if not port_downwind.empty:
                        best_port = port_downwind.loc[port_downwind['angle_to_wind'].idxmax()]
                        best_port_downwind = {
                            "angle": best_port['angle_to_wind'],
                            "speed": best_port['avg_speed_knots']  # Speed is already in knots in the UI
                        }
                    
                    # Find best starboard tack downwind angle
                    if not starboard_downwind.empty:
                        best_starboard = starboard_downwind.loc[starboard_downwind['angle_to_wind'].idxmax()]
                        best_starboard_downwind = {
                            "angle": best_starboard['angle_to_wind'],
                            "speed": best_starboard['avg_speed_knots']  # Speed is already in knots in the UI
                        }
        
        # Get average angles if available in session state
        angle_results = session_state.get('angle_results', {})
        avg_angle = angle_results.get('average_angle')
        port_angle = angle_results.get('port_average')
        starboard_angle = angle_results.get('starboard_average')
        angle_diff = None
        if port_angle is not None and starboard_angle is not None:
            angle_diff = abs(port_angle - starboard_angle)
        
        # Create the GearItem with data from session state
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            track_name=session_state.get('track_name'),
            date=metrics.get('date'),
            wind_direction=session_state.get('wind_direction'),
            avg_speed=metrics.get('weighted_avg_speed', metrics.get('avg_speed')),
            max_speed=metrics.get('max_speed'),
            distance=metrics.get('distance'),
            duration=metrics.get('duration').total_seconds() / 60 if metrics.get('duration') else None,
            active_duration=metrics.get('active_duration').total_seconds() / 60 if metrics.get('active_duration') else None,
            upwind_progress_speed=upwind_progress,  # Legacy field
            vmg_upwind=vmg_upwind,
            best_port_upwind_angle=best_port_upwind["angle"],
            best_port_upwind_speed=best_port_upwind["speed"],
            best_starboard_upwind_angle=best_starboard_upwind["angle"],
            best_starboard_upwind_speed=best_starboard_upwind["speed"],
            best_port_downwind_angle=best_port_downwind["angle"],
            best_port_downwind_speed=best_port_downwind["speed"],
            best_starboard_downwind_angle=best_starboard_downwind["angle"],
            best_starboard_downwind_speed=best_starboard_downwind["speed"],
            avg_upwind_angle=avg_angle,
            avg_port_tack_angle=port_angle,
            avg_starboard_tack_angle=starboard_angle,
            port_starboard_diff=angle_diff,
            source_file=session_state.get('current_file_name')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert GearItem to a dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the GearItem
        """
        return {
            key: value for key, value in self.__dict__.items()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GearItem":
        """Create a GearItem from a dictionary.
        
        Args:
            data: Dictionary containing GearItem data
            
        Returns:
            GearItem: New GearItem instance from the dictionary
        """
        return cls(**data)
