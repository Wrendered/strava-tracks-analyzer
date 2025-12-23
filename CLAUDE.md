# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Foil Lab Backend** is a FastAPI-based REST API for wingfoil/sailing GPS track analysis. It provides the core algorithms for:
- GPX file parsing and track segmentation
- Wind direction estimation (iterative algorithm with tack reclassification)
- Performance metrics calculation (VMG, angles, speeds)
- Gear comparison analysis

The frontend is in a separate repository: `foil-lab-web` (Next.js/React).

## Repository Structure

```
strava-tracks-analyzer/
├── api/
│   └── main.py                 # FastAPI endpoints
├── core/                       # Core algorithms (pure functions)
│   ├── gpx.py                  # GPX file parsing
│   ├── segments/               # Track segmentation
│   ├── wind/                   # Wind estimation
│   │   ├── algorithms.py       # Main algorithms (iterative + weighted)
│   │   ├── factory.py          # Algorithm factory pattern
│   │   └── models.py           # WindEstimate dataclass
│   ├── metrics.py              # Basic metrics
│   ├── metrics_advanced.py     # VMG, quality scoring
│   ├── calculations.py         # Wind angle calculations
│   └── constants.py            # Algorithm constants
├── services/
│   ├── track_analysis_service.py   # Main analysis pipeline
│   └── wind_service.py             # Wind estimation service
├── config/
│   └── settings.py             # Default parameters
├── utils/
│   ├── segment_analysis.py     # Segment utilities
│   └── parameter_scaling.py    # Adaptive scaling
├── tests/                      # Test suite
├── docs/                       # Documentation
├── data/                       # Sample GPX files
├── run_api.py                  # Dev server script
└── requirements.txt            # Python dependencies
```

## Key Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run API server (development)
python run_api.py
# or
uvicorn api.main:app --reload --port 8000

# Run tests
python -m pytest tests/

# Test API manually
python tests/test_api.py
```

## API Endpoints

### `GET /api/health`
Health check endpoint.

### `GET /api/config`
Returns default parameters and valid ranges for the frontend.

### `POST /api/analyze-track`
Main analysis endpoint. Accepts GPX file upload with parameters:
- `wind_direction` (float): Initial wind estimate (degrees)
- `angle_tolerance` (float): Max bearing variation in segments
- `min_duration` (float): Minimum segment duration (seconds)
- `min_distance` (float): Minimum segment distance (meters)
- `min_speed` (float): Minimum speed threshold (knots)
- `suspicious_angle_threshold` (float): Filter unrealistic angles

Returns: segments, wind estimate, performance metrics, track summary.

### `POST /api/estimate-wind`
Standalone wind estimation (supports method selection: iterative, weighted).

## Wind Estimation Algorithm

The **iterative algorithm** (`core/wind/algorithms.py`) is the production algorithm:

1. Start with user's initial wind estimate
2. Classify segments as port/starboard tack
3. Calculate median angles for each tack
4. Adjust wind to balance port/starboard angles
5. **Reclassify segments with new wind** (key fix)
6. Repeat until convergence (<0.5° change)

This fixes the bug where tacks classified once were never updated.

## Technical Concepts

### Wind Direction
- Wind direction = where wind comes FROM (0°=N, 90°=E, 180°=S, 270°=W)
- Example: 270° means wind blowing FROM west TO east

### Key Metrics
- **Segments**: Consistent sailing stretches with stable bearing
- **Tacks**: Port (wind from left) vs Starboard (wind from right)
- **VMG**: Velocity Made Good = Speed × cos(angle to wind)
- **Angle to Wind**: Degrees off wind direction (45° typical sailboat, 60° wingfoil)

### Confidence Levels
- **High**: Both tacks present, angles balanced (<10° diff), sufficient data
- **Medium**: Both tacks, moderate balance (<20° diff)
- **Low**: Missing tack or poor balance

## Deployment

**Production**: Railway
- URL: https://strava-tracks-analyzer-production.up.railway.app
- Auto-deploys from `main` branch

**Frontend**: Vercel (foil-lab-web repo)
- URL: https://foil-lab-web.vercel.app

## Development Workflow

### Adding Features
1. Implement in `core/` (pure functions, no framework dependencies)
2. Add service layer in `services/` if needed
3. Expose via API in `api/main.py`
4. Update frontend in foil-lab-web repo

### Adding Parameters
1. Add default to `config/settings.py`
2. Add constant to `core/constants.py` if algorithm-related
3. Update `/api/config` endpoint ranges
4. Frontend fetches dynamically

## Related Repository

**foil-lab-web** (Next.js frontend)
- Modern React UI with TypeScript
- Communicates via this API
- Deployed on Vercel
