# Foil Lab Architecture

## System Overview

Foil Lab is a two-repository system for analyzing wingfoil/sailing GPS tracks:

- **strava-tracks-analyzer** (this repo): FastAPI backend with core algorithms
- **foil-lab-web**: Next.js/React frontend

## High-Level Architecture

```
┌─────────────────────────────────────┐
│         Next.js Frontend            │
│         (foil-lab-web)              │
│                                     │
│    • File upload UI                 │
│    • Parameter controls             │
│    • Map visualization              │
│    • Polar plots                    │
│                                     │
│    Deployed: Vercel                 │
└──────────────┬──────────────────────┘
               │
               │ HTTPS/REST
               ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│     (strava-tracks-analyzer)        │
│                                     │
│    • GPX parsing                    │
│    • Segment detection              │
│    • Wind estimation                │
│    • Performance metrics            │
│                                     │
│    Deployed: Railway                │
└─────────────────────────────────────┘
```

## Repository Structure

```
strava-tracks-analyzer/
├── api/
│   └── main.py                 # FastAPI endpoints
├── core/                       # Core algorithms (pure functions)
│   ├── gpx.py                  # GPX file parsing
│   ├── segments/               # Track segmentation
│   │   ├── detector.py         # Segment detection
│   │   └── analyzer.py         # Segment analysis
│   ├── wind/                   # Wind estimation
│   │   ├── algorithms.py       # Iterative algorithm
│   │   ├── factory.py          # Algorithm factory
│   │   └── models.py           # WindEstimate dataclass
│   ├── calculations.py         # Wind angle calculations
│   ├── metrics.py              # Basic metrics
│   ├── metrics_advanced.py     # VMG, quality scoring
│   ├── constants.py            # Algorithm constants
│   ├── validation.py           # Input validation
│   └── models/                 # Domain models
│       ├── segment.py
│       ├── track.py
│       └── gear_item.py
├── services/                   # Business logic layer
│   ├── track_analysis_service.py   # Main analysis pipeline
│   └── wind_service.py             # Wind estimation service
├── config/
│   └── settings.py             # Default parameters
├── utils/                      # Helper utilities
│   ├── segment_analysis.py     # Segment quality checks
│   ├── geo.py                  # Unit conversions
│   └── test_data_generator.py  # Test data generation
├── tests/                      # Test suite
├── docs/                       # Documentation
└── data/                       # Sample GPX files
```

## Data Flow

### Track Analysis Pipeline

```
POST /api/analyze-track
        │
        ▼
┌─────────────────────────────────┐
│  GPX Parser (core/gpx.py)       │
│  Parse file → DataFrame         │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Segment Detector               │
│  (core/segments/detector.py)    │
│  Find consistent angle stretches│
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Wind Estimator                 │
│  (core/wind/algorithms.py)      │
│  Iterative tack balancing       │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Metrics Calculator             │
│  (core/metrics_advanced.py)     │
│  VMG, angles, performance       │
└───────────────┬─────────────────┘
                │
                ▼
        JSON Response
```

## Key Design Principles

1. **API-Only Backend**: No UI code, just REST endpoints
2. **Pure Functions**: Core algorithms are stateless and testable
3. **Single Responsibility**: Each module has one clear purpose
4. **Framework Independence**: Core logic has no web framework dependencies
5. **Configuration Centralized**: All defaults in `config/settings.py`

## Layer Responsibilities

### API Layer (`api/`)
- HTTP request/response handling
- Input validation
- Error responses
- CORS configuration

### Service Layer (`services/`)
- Orchestrates core algorithms
- Business logic coordination
- Result aggregation

### Core Layer (`core/`)
- Pure algorithm implementations
- No side effects
- Framework-agnostic
- Fully testable

### Utils Layer (`utils/`)
- Helper functions
- Unit conversions
- Quality checks

## Deployment

```
┌─────────────────┐         ┌─────────────────┐
│    Next.js      │         │    FastAPI      │
│    Vercel       │ ──────► │    Railway      │
│                 │  HTTPS  │                 │
└─────────────────┘         └─────────────────┘

Frontend URL: https://foil-lab-web.vercel.app
Backend URL:  https://strava-tracks-analyzer-production.up.railway.app
```

Both deploy automatically from their respective `main` branches.
