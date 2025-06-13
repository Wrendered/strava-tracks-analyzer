# API Enhancement Plan for React Migration

## Overview

This document outlines the API enhancements needed to support the new React frontend while maintaining backward compatibility with the existing Streamlit application.

## Current API Analysis

### Existing Endpoints
- `POST /api/analyze-track` - Core track analysis
- `GET /api/config` - Configuration parameters
- `GET /api/health` - Health check

### Current Limitations
1. **Single Analysis Endpoint**: Monolithic response, no granular data access
2. **No Real-time Updates**: No support for parameter changes without full reanalysis
3. **Limited Error Handling**: Basic error responses
4. **No Caching**: No intelligent caching for expensive operations
5. **No Batch Operations**: No support for gear comparison workflows

## Enhanced API Design

### 1. Modular Analysis Endpoints

#### Session Management
```
POST /api/sessions
GET /api/sessions/{session_id}
DELETE /api/sessions/{session_id}
```

#### Track Operations
```
POST /api/sessions/{session_id}/tracks
GET /api/sessions/{session_id}/tracks/{track_id}
DELETE /api/sessions/{session_id}/tracks/{track_id}
PUT /api/sessions/{session_id}/tracks/{track_id}/parameters
```

#### Analysis Components
```
GET /api/sessions/{session_id}/tracks/{track_id}/segments
GET /api/sessions/{session_id}/tracks/{track_id}/wind-analysis
GET /api/sessions/{session_id}/tracks/{track_id}/vmg-analysis
GET /api/sessions/{session_id}/tracks/{track_id}/performance-stats
```

### 2. Real-time Parameter Updates

#### Wind Direction Override
```
PUT /api/sessions/{session_id}/tracks/{track_id}/wind-override
{
  "wind_direction": 270.0,
  "recalculate_segments": true
}
```

#### Parameter Updates with Incremental Recalculation
```
PATCH /api/sessions/{session_id}/tracks/{track_id}/parameters
{
  "angle_tolerance": 25,
  "min_speed": 8.0,
  "affected_components": ["segments", "vmg"]
}
```

### 3. Streaming and Progressive Loading

#### Large File Upload with Progress
```
POST /api/upload/tracks (multipart/form-data with chunking)
WebSocket: /ws/upload-progress/{upload_id}
```

#### Streaming Analysis Results
```
WebSocket: /ws/analysis/{session_id}/{track_id}
Events: segments_detected, wind_estimated, vmg_calculated, analysis_complete
```

### 4. Gear Comparison Enhancements

#### Bulk Operations
```
POST /api/gear-comparisons
POST /api/gear-comparisons/{comparison_id}/tracks (bulk upload)
GET /api/gear-comparisons/{comparison_id}/results
```

#### Export Operations
```
GET /api/gear-comparisons/{comparison_id}/export?format=csv|json|excel
POST /api/sessions/{session_id}/export (single track export)
```

### 5. Caching and Performance

#### Smart Caching Strategy
- **Segments**: Cache by file hash + parameters
- **Wind Analysis**: Cache by segments hash
- **VMG Analysis**: Cache by segments + wind direction
- **Visualizations**: Cache rendered data

#### Cache Management Endpoints
```
GET /api/cache/status
DELETE /api/cache/{cache_key}
POST /api/cache/warm (preload common configurations)
```

## Implementation Plan

### Phase 1: Session Management (Week 1)
```python
# New session service
class AnalysisSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.tracks = {}
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
    
    def add_track(self, file_data, metadata):
        track_id = generate_track_id()
        # Store track with initial analysis
        return track_id
    
    def update_parameters(self, track_id, parameters):
        # Intelligent recalculation based on what changed
        pass
```

### Phase 2: Real-time Updates (Week 2)
```python
# WebSocket handler for real-time updates
@websocket_endpoint("/ws/analysis/{session_id}/{track_id}")
async def analysis_websocket(websocket, session_id, track_id):
    # Send incremental updates as analysis progresses
    pass

# Incremental recalculation service
class IncrementalAnalysis:
    def update_wind_direction(self, track_id, new_wind):
        # Only recalculate wind-dependent components
        pass
    
    def update_parameters(self, track_id, params):
        # Determine minimal recalculation needed
        pass
```

### Phase 3: Performance Optimization (Week 3)
```python
# Intelligent caching with Redis
class AnalysisCache:
    def get_segments(self, file_hash, params_hash):
        cache_key = f"segments:{file_hash}:{params_hash}"
        return redis.get(cache_key)
    
    def cache_segments(self, file_hash, params_hash, segments):
        cache_key = f"segments:{file_hash}:{params_hash}"
        redis.setex(cache_key, 3600, segments)  # 1 hour TTL
```

### Phase 4: Streaming and Bulk Operations (Week 4)
```python
# Streaming file upload
@app.post("/api/upload/tracks")
async def upload_track_stream(request: Request):
    # Handle chunked upload with progress updates
    pass

# Bulk analysis for gear comparison
@app.post("/api/gear-comparisons/{comparison_id}/analyze-bulk")
async def analyze_bulk_tracks(comparison_id: str, background_tasks: BackgroundTasks):
    # Queue analysis jobs and return immediately
    pass
```

## New Response Formats

### Standardized API Responses
```python
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    timestamp: datetime
    request_id: str

class PaginatedResponse(APIResponse):
    data: List[Any]
    pagination: PaginationInfo

class AnalysisResponse(APIResponse):
    data: AnalysisResult
    cache_info: CacheInfo
    processing_time: float
```

### Granular Data Models
```python
class TrackSegments(BaseModel):
    segments: List[Segment]
    total_segments: int
    upwind_count: int
    downwind_count: int
    suspicious_count: int

class WindAnalysis(BaseModel):
    estimated_direction: float
    confidence: str
    algorithm_used: str
    port_starboard_difference: float
    refinement_applied: bool

class VMGAnalysis(BaseModel):
    upwind_vmg: Optional[float]
    downwind_vmg: Optional[float]
    vmg_segments: List[int]  # Segment indices
    best_angles: Dict[str, float]
    calculation_details: VMGDetails
```

## Error Handling Enhancements

### Structured Error Responses
```python
class APIError(BaseModel):
    code: str
    message: str
    details: Optional[Dict] = None
    suggestions: Optional[List[str]] = None

# Error types
TRACK_PROCESSING_ERRORS = {
    "INVALID_GPX": "GPX file format is invalid",
    "NO_SEGMENTS": "No valid segments detected",
    "INSUFFICIENT_DATA": "Track too short for analysis"
}
```

### Validation and Input Sanitization
```python
from pydantic import BaseModel, validator

class AnalysisParameters(BaseModel):
    wind_direction: float
    angle_tolerance: float
    min_speed: float
    min_distance: float
    min_duration: float
    
    @validator('wind_direction')
    def validate_wind_direction(cls, v):
        if not 0 <= v < 360:
            raise ValueError('Wind direction must be between 0 and 359 degrees')
        return v
```

## Security Enhancements

### Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/analyze-track")
@limiter.limit("10/minute")  # 10 analyses per minute
async def analyze_track():
    pass
```

### Input Validation and File Security
```python
def validate_gpx_file(file_data: bytes) -> bool:
    # Validate file size, content type, XML structure
    if len(file_data) > MAX_FILE_SIZE:
        raise ValueError("File too large")
    
    # Parse XML safely
    try:
        root = ET.fromstring(file_data)
        if root.tag != '{http://www.topografix.com/GPX/1/1}gpx':
            raise ValueError("Invalid GPX format")
    except ET.ParseError:
        raise ValueError("Invalid XML structure")
    
    return True
```

## Monitoring and Analytics

### Performance Metrics
```python
import time
from contextlib import contextmanager

@contextmanager
def track_performance(operation: str):
    start = time.time()
    yield
    duration = time.time() - start
    metrics.record_operation_time(operation, duration)

# Usage
async def analyze_track():
    with track_performance("track_analysis"):
        # Analysis logic
        pass
```

### User Analytics
```python
class AnalyticsEvent(BaseModel):
    event_type: str
    user_id: Optional[str]
    session_id: str
    properties: Dict
    timestamp: datetime

# Track usage patterns
analytics.track("track_uploaded", {
    "file_size": len(file_data),
    "track_duration": track_duration,
    "segments_detected": len(segments)
})
```

## Backward Compatibility

### Legacy Endpoint Support
```python
@app.post("/api/analyze-track")
async def legacy_analyze_track(file: UploadFile):
    # Maintain existing interface while using new backend
    session = create_temporary_session()
    track_id = await session.add_track(file)
    result = await session.get_complete_analysis(track_id)
    return convert_to_legacy_format(result)
```

## Testing Strategy

### API Testing
```python
import pytest
from fastapi.testclient import TestClient

def test_session_lifecycle():
    # Test session creation, track upload, analysis, cleanup
    pass

def test_incremental_updates():
    # Test parameter changes trigger minimal recalculation
    pass

def test_error_handling():
    # Test all error scenarios with appropriate responses
    pass
```

### Performance Testing
```python
def test_concurrent_analysis():
    # Test multiple simultaneous analyses
    pass

def test_large_file_handling():
    # Test files at size limits
    pass

def test_cache_effectiveness():
    # Verify cache hit rates and performance improvements
    pass
```

## Deployment Considerations

### Database Changes
- Add session storage (Redis/PostgreSQL)
- Implement cache layer
- Add analytics storage

### Infrastructure Updates
- WebSocket support
- File upload optimization
- Background job processing (Celery/RQ)

### Monitoring
- API response times
- Error rates by endpoint
- Cache hit rates
- User session metrics

This enhanced API will provide the foundation for a world-class React frontend while maintaining the robustness and accuracy of the current analysis engine.