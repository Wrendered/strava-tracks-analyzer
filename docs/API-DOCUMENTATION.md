# Foil Lab API Documentation

## Overview

The Foil Lab API provides REST endpoints for analyzing wingfoil/sailing GPS tracks. Built with FastAPI, it exposes the core analysis algorithms for use by any frontend application.

**Base URL**: `https://strava-tracks-analyzer-production.up.railway.app`

## Authentication

Currently, the API is open and does not require authentication. This may change in future versions.

## Endpoints

### Health Check

Check if the API service is running and healthy.

**Endpoint**: `GET /api/health`

**Response**:
```json
{
  "status": "healthy",
  "service": "foil-lab-api"
}
```

**Status Codes**:
- `200 OK`: Service is healthy

---

### Get Configuration

Retrieve default parameter values and their valid ranges. This endpoint should be called on application startup to ensure UI controls are properly configured.

**Endpoint**: `GET /api/config`

**Response**:
```json
{
  "defaults": {
    "wind_direction": 90.0,
    "angle_tolerance": 25,
    "min_duration": 15,
    "min_distance": 75,
    "min_speed": 8.0,
    "suspicious_angle_threshold": 25
  },
  "ranges": {
    "wind_direction": {
      "min": 0,
      "max": 359,
      "step": 1
    },
    "angle_tolerance": {
      "min": 5,
      "max": 45,
      "step": 1
    },
    "min_duration": {
      "min": 5,
      "max": 60,
      "step": 1
    },
    "min_distance": {
      "min": 10,
      "max": 200,
      "step": 10
    },
    "min_speed": {
      "min": 3,
      "max": 15,
      "step": 0.5
    },
    "suspicious_angle_threshold": {
      "min": 15,
      "max": 35,
      "step": 1
    }
  }
}
```

**Status Codes**:
- `200 OK`: Configuration retrieved successfully

---

### Analyze Track

Analyze a GPX track file to detect sailing segments, estimate wind direction, and calculate performance metrics.

**Endpoint**: `POST /api/analyze-track`

**Request**:
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: 
  - `file`: GPX file (required)
- **Query Parameters**:
  - `wind_direction` (float, optional): Initial wind direction estimate in degrees (0-359). Default: 90.0
  - `angle_tolerance` (float, optional): Maximum angle variation within segments in degrees. Default: 25.0
  - `min_duration` (float, optional): Minimum segment duration in seconds. Default: 15.0
  - `min_distance` (float, optional): Minimum segment distance in meters. Default: 75.0
  - `min_speed` (float, optional): Minimum speed in knots. Default: 8.0
  - `suspicious_angle_threshold` (float, optional): Threshold for filtering suspicious angles in degrees. Default: 25.0

**Example Request**:
```bash
curl -X POST "https://api.example.com/api/analyze-track?wind_direction=270&min_duration=10" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@track.gpx"
```

**Response**:
```json
{
  "segments": [
    {
      "start_time": "2024-01-15T10:30:00Z",
      "end_time": "2024-01-15T10:32:30Z",
      "duration_seconds": 150,
      "distance_meters": 450.5,
      "avg_speed_knots": 12.3,
      "max_speed_knots": 15.2,
      "bearing": 45.0,
      "is_upwind": true,
      "angle_to_wind": 42.0,
      "tack": "starboard"
    }
  ],
  "wind_estimate": {
    "direction": 268.5,
    "confidence": "High",
    "port_average_angle": 44.2,
    "starboard_average_angle": 43.8,
    "total_segments": 24,
    "port_segments": 12,
    "starboard_segments": 12
  },
  "performance_metrics": {
    "avg_speed": 11.5,
    "avg_upwind_angle": 44.0,
    "best_upwind_angle": 38.0,
    "vmg_upwind": 8.2,
    "vmg_downwind": 10.5,
    "port_tack_count": 12,
    "starboard_tack_count": 12
  },
  "track_summary": {
    "total_distance": 15.2,
    "duration_seconds": 3600,
    "avg_speed_knots": 11.5,
    "max_speed_knots": 22.3,
    "filename": "track.gpx"
  }
}
```

**Response Fields**:

- **segments**: Array of detected sailing segments
  - `start_time`: ISO 8601 timestamp of segment start
  - `end_time`: ISO 8601 timestamp of segment end
  - `duration_seconds`: Segment duration in seconds
  - `distance_meters`: Distance covered in meters
  - `avg_speed_knots`: Average speed in knots
  - `max_speed_knots`: Maximum speed in knots
  - `bearing`: Average compass bearing in degrees
  - `is_upwind`: Boolean indicating if segment is upwind
  - `angle_to_wind`: Angle relative to wind in degrees
  - `tack`: "port" or "starboard"

- **wind_estimate**: Wind direction estimation results
  - `direction`: Estimated wind direction in degrees (0-359)
  - `confidence`: "High", "Medium", "Low", or "None"
  - `port_average_angle`: Average angle on port tack
  - `starboard_average_angle`: Average angle on starboard tack
  - `total_segments`: Total number of segments analyzed
  - `port_segments`: Number of port tack segments
  - `starboard_segments`: Number of starboard tack segments

- **performance_metrics**: Calculated performance statistics
  - `avg_speed`: Average speed in knots (nullable)
  - `avg_upwind_angle`: Average upwind angle in degrees (nullable)
  - `best_upwind_angle`: Best (smallest) upwind angle in degrees (nullable)
  - `vmg_upwind`: Velocity Made Good upwind in knots (nullable)
  - `vmg_downwind`: Velocity Made Good downwind in knots (nullable)
  - `port_tack_count`: Number of port tacks
  - `starboard_tack_count`: Number of starboard tacks

- **track_summary**: Overall track information
  - `total_distance`: Total distance in kilometers
  - `duration_seconds`: Total duration in seconds
  - `avg_speed_knots`: Overall average speed in knots
  - `max_speed_knots`: Maximum speed achieved in knots
  - `filename`: Original filename

**Status Codes**:
- `200 OK`: Analysis completed successfully
- `400 Bad Request`: Invalid file format or parameters
- `422 Unprocessable Entity`: File parsing error
- `500 Internal Server Error`: Analysis error

**Error Response**:
```json
{
  "detail": "File must be a GPX file"
}
```

---

## Error Handling

All endpoints return standard HTTP status codes and JSON error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common error scenarios:
- Invalid GPX file format
- Empty or corrupted file
- Invalid parameter values
- Server processing errors

---

## Rate Limiting

Currently, there are no rate limits implemented. This may change based on usage patterns.

---

## CORS Configuration

The API is configured to accept requests from any origin (`*`) to support frontend development. In production, this should be restricted to specific domains.

---

## Data Processing Notes

### Wind Direction
- Wind direction represents where the wind is coming FROM
- 0° = North, 90° = East, 180° = South, 270° = West
- The algorithm uses an iterative refinement process

### Segment Detection
- Segments are detected based on consistent bearing/heading
- Adaptive parameters scale with track duration for long sessions
- Short segments below thresholds are filtered out

### Performance Calculations
- VMG (Velocity Made Good) uses distance-weighted averaging
- Upwind angles are measured relative to estimated wind direction
- Best angles represent optimal performance achieved

---

## Integration Examples

### JavaScript/TypeScript
```typescript
const formData = new FormData();
formData.append('file', gpxFile);

const response = await fetch(
  'https://api.example.com/api/analyze-track?wind_direction=270',
  {
    method: 'POST',
    body: formData
  }
);

const result = await response.json();
```

### Python
```python
import requests

files = {'file': open('track.gpx', 'rb')}
params = {
    'wind_direction': 270,
    'min_duration': 10
}

response = requests.post(
    'https://api.example.com/api/analyze-track',
    files=files,
    params=params
)

result = response.json()
```

---

## Webhook Support

Webhooks are not currently supported but may be added for long-running analysis tasks in the future.

---

## Versioning

The API currently does not use versioning. Breaking changes will be communicated in advance.

---

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/Wrendered/strava-tracks-analyzer/issues
- Documentation: See CLAUDE.md files in the repository