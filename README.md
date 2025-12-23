# Foil Lab Backend

FastAPI backend for wingfoil/sailing GPS track analysis. Parses GPX files, detects sailing segments, estimates wind direction, and calculates performance metrics.

**Frontend**: [foil-lab-web](https://github.com/Wrendered/foil-lab-web) (Next.js/React)

**Live API**: https://strava-tracks-analyzer-production.up.railway.app

## Features

- **GPX Parsing**: Load and process GPS tracks from Strava or other sources
- **Segment Detection**: Find consistent sailing stretches with stable bearing
- **Wind Estimation**: Iterative algorithm that balances port/starboard tack angles
- **Performance Metrics**: VMG (Velocity Made Good), upwind angles, speeds
- **Gear Comparison**: AI-powered analysis of different equipment setups

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
python run_api.py

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/config` | GET | Default parameters and ranges |
| `/api/analyze-track` | POST | Analyze GPX file |
| `/api/estimate-wind` | POST | Standalone wind estimation |

### Example: Analyze a Track

```bash
curl -X POST "http://localhost:8000/api/analyze-track" \
  -F "file=@session.gpx" \
  -F "wind_direction=270" \
  -F "min_speed=5"
```

## Project Structure

```
├── api/main.py              # FastAPI endpoints
├── core/                    # Core algorithms
│   ├── wind/algorithms.py   # Wind estimation (iterative)
│   ├── segments/            # Track segmentation
│   ├── gpx.py               # GPX parsing
│   └── metrics*.py          # Performance calculations
├── services/                # Business logic layer
├── config/settings.py       # Default parameters
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Wind Estimation

The iterative algorithm estimates wind direction by:

1. Classifying segments as port/starboard tack
2. Calculating median upwind angles for each tack
3. Adjusting wind to balance the angles
4. **Reclassifying segments** with the new wind estimate
5. Repeating until convergence

This fixes the common bug where tacks are classified once and never updated as the wind estimate changes.

## Deployment

Deployed on Railway, auto-deploys from `main` branch.

```bash
# Environment variables (Railway dashboard)
# None required for basic operation
# ANTHROPIC_API_KEY - for AI gear comparison features
```

## Development

```bash
# Run tests
python -m pytest tests/

# Type check
mypy core/ services/ api/

# Lint
ruff check .
```

## License

MIT
