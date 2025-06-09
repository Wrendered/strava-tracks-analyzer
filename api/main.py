"""
FastAPI backend for Foil Lab.

This provides REST API endpoints for track analysis, wind estimation,
and other core algorithms, enabling framework-agnostic frontend development.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging
import io
import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Foil Lab API",
    description="Backend API for wingfoil GPS track analysis",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Next.js domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize state management with memory adapters (no UI state needed!)
from adapters.memory_state import register_memory_adapters
register_memory_adapters()

# Import our services
from services.track_analysis_service import analyze_track_data, TrackAnalysisResult
from services.wind_service import get_wind_service
from core.gpx import load_gpx_file


# Pydantic models for API requests/responses
class AnalysisParameters(BaseModel):
    wind_direction: float = 90.0
    angle_tolerance: float = 25.0
    min_duration: float = 10.0
    min_distance: float = 50.0
    min_speed: float = 5.0
    suspicious_angle_threshold: float = 20.0


class WindEstimateResponse(BaseModel):
    direction: float
    confidence: str
    port_average_angle: float
    starboard_average_angle: float
    total_segments: int
    port_segments: int
    starboard_segments: int


class PerformanceMetrics(BaseModel):
    avg_speed: Optional[float]
    avg_upwind_angle: Optional[float]
    best_upwind_angle: Optional[float]
    vmg_upwind: Optional[float]
    vmg_downwind: Optional[float]
    port_tack_count: int
    starboard_tack_count: int


class TrackAnalysisResponse(BaseModel):
    segments: List[Dict[str, Any]]
    wind_estimate: WindEstimateResponse
    performance_metrics: PerformanceMetrics
    track_summary: Dict[str, Any]


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Foil Lab API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/analyze-track": "Analyze a GPX track file",
            "GET /api/health": "Health check endpoint"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "foil-lab-api"}


@app.post("/api/analyze-track", response_model=TrackAnalysisResponse)
async def analyze_track(
    file: UploadFile = File(...),
    wind_direction: float = 90.0,
    angle_tolerance: float = 25.0,
    min_duration: float = 10.0,
    min_distance: float = 50.0,
    min_speed: float = 5.0,
    suspicious_angle_threshold: float = 20.0
):
    """
    Analyze a GPX track file.
    
    Args:
        file: GPX file to analyze
        wind_direction: Initial wind direction estimate (0-359 degrees)
        angle_tolerance: Maximum angle variation within segments
        min_duration: Minimum segment duration in seconds
        min_distance: Minimum segment distance in meters
        min_speed: Minimum speed in knots
        suspicious_angle_threshold: Threshold for filtering suspicious angles
        
    Returns:
        Analysis results including segments, wind estimate, and performance metrics
    """
    try:
        # Validate file type
        if not file.filename.endswith('.gpx'):
            raise HTTPException(status_code=400, detail="File must be a GPX file")
        
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # Load GPX data
        logger.info(f"Processing file: {file.filename}")
        track_data = load_gpx_file(file_obj, file.filename)
        
        if track_data.empty:
            raise HTTPException(status_code=400, detail="No valid track data found in GPX file")
        
        # Use our track analysis function
        result = analyze_track_data(
            track_data=track_data,
            initial_wind_direction=wind_direction,
            filename=file.filename,
            angle_tolerance=angle_tolerance,
            min_duration=min_duration,
            min_distance=min_distance,
            min_speed=min_speed,
            suspicious_angle_threshold=suspicious_angle_threshold
        )
        
        # Count tacks
        port_tack_count = len(result.segments[result.segments.get('tack', '') == 'Port']) if 'tack' in result.segments.columns else 0
        starboard_tack_count = len(result.segments[result.segments.get('tack', '') == 'Starboard']) if 'tack' in result.segments.columns else 0
        
        # Prepare response
        response = TrackAnalysisResponse(
            segments=[segment.to_dict() for _, segment in result.segments.iterrows()],
            wind_estimate=WindEstimateResponse(
                direction=result.refined_wind,
                confidence=result.wind_confidence,
                port_average_angle=result.best_port_angle or 0,
                starboard_average_angle=result.best_starboard_angle or 0,
                total_segments=len(result.segments),
                port_segments=port_tack_count,
                starboard_segments=starboard_tack_count
            ),
            performance_metrics=PerformanceMetrics(
                avg_speed=result.avg_speed,
                avg_upwind_angle=result.avg_upwind_angle,
                best_upwind_angle=min(filter(None, [result.best_port_angle, result.best_starboard_angle]), default=None),
                vmg_upwind=result.vmg_upwind,
                vmg_downwind=None,  # Not calculated in current implementation
                port_tack_count=port_tack_count,
                starboard_tack_count=starboard_tack_count
            ),
            track_summary={
                'total_distance': float(result.total_distance),
                'duration_seconds': float(len(result.track_data)),
                'avg_speed_knots': float(result.avg_speed),
                'max_speed_knots': float(result.max_speed),
                'filename': file.filename
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing track: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing track: {str(e)}")


@app.post("/api/estimate-wind")
async def estimate_wind(
    file: UploadFile = File(...),
    initial_wind_direction: float = 90.0,
    method: str = "iterative"
):
    """
    Estimate wind direction from a GPX track.
    
    Args:
        file: GPX file to analyze
        initial_wind_direction: Starting estimate for wind direction
        method: Estimation method (iterative, weighted, or basic)
        
    Returns:
        Wind direction estimate with confidence
    """
    try:
        # Read and process file
        content = await file.read()
        file_obj = io.BytesIO(content)
        track_data = load_gpx_file(file_obj, file.filename)
        
        if track_data.empty:
            raise HTTPException(status_code=400, detail="No valid track data found")
        
        # Detect segments
        from core.segments import find_consistent_angle_stretches
        segments = find_consistent_angle_stretches(track_data)
        
        if segments.empty:
            raise HTTPException(status_code=400, detail="No segments detected")
        
        # Estimate wind direction
        wind_service = get_wind_service()
        wind_estimate = wind_service.estimate_wind_direction(
            segments=segments,
            method=method
        )
        
        return WindEstimateResponse(
            direction=wind_estimate.direction,
            confidence=wind_estimate.confidence,
            port_average_angle=wind_estimate.port_average_angle,
            starboard_average_angle=wind_estimate.starboard_average_angle,
            total_segments=wind_estimate.total_segments,
            port_segments=wind_estimate.port_segments,
            starboard_segments=wind_estimate.starboard_segments
        )
        
    except Exception as e:
        logger.error(f"Error estimating wind: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error estimating wind: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)