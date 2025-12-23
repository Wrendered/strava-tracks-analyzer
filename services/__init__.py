"""
Services package.

Provides business logic layer between API and core algorithms.

Modules:
    track_analysis_service: Main analysis pipeline for GPX tracks
    wind_service: Wind direction estimation and VMG calculations
"""

from services.track_analysis_service import analyze_track_data, TrackAnalysisResult
from services.wind_service import WindService, get_wind_service

__all__ = [
    'analyze_track_data',
    'TrackAnalysisResult',
    'WindService',
    'get_wind_service',
]
