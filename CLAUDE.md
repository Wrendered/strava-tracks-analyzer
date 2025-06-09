# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Foil Lab** is a comprehensive wingfoil/sailing track analysis platform with multiple frontends:
- **Streamlit App**: Original full-featured web interface (this repository)
- **FastAPI Backend**: REST API serving core algorithms (`api/` directory)
- **Next.js Frontend**: Modern React-based UI (separate `foil-lab-web` repository)

The system analyzes GPS tracks from GPX files, detects sailing segments, estimates wind direction, calculates performance metrics (VMG, angles), and enables gear comparison.

## Repository Structure

```
📁 strava-tracks-analyzer/              # Parent directory
├── 📁 strava-tracks-analyzer/          # This repository (Python backend + Streamlit)
│   ├── api/                            # FastAPI REST backend
│   │   └── main.py                     # API endpoints
│   ├── core/                           # Business logic (framework-agnostic)
│   │   ├── models/                     # Domain models
│   │   ├── gpx.py                      # GPX parsing
│   │   ├── metrics.py                  # Performance calculations
│   │   ├── segments/                   # Segment detection
│   │   └── wind/                       # Wind estimation algorithms
│   ├── services/                       # Service layer with state management
│   │   ├── state.py                    # Abstract state interfaces
│   │   ├── track_analysis_service.py   # Unified analysis pipeline
│   │   ├── wind_service.py             # Wind estimation service
│   │   └── segment_service.py          # Segment operations
│   ├── adapters/                       # Framework adapters
│   │   ├── streamlit_state.py          # Streamlit state implementation
│   │   └── memory_state.py             # In-memory state for API/testing
│   ├── ui/                             # Streamlit UI components
│   │   ├── pages/                      # Application pages
│   │   └── components/                 # Reusable UI elements
│   ├── config/                         # Configuration
│   │   └── settings.py                 # Default parameters
│   ├── utils/                          # Utilities
│   ├── tests/                          # Test suite
│   ├── data/                           # Test GPX files
│   ├── requirements.txt                # Python dependencies
│   └── app.py                          # Streamlit entry point
│
└── 📁 foil-lab-web/                    # Next.js frontend (separate repo)
    ├── app/                            # Next.js app directory
    ├── components/                     # React components
    ├── lib/                            # API client and utilities
    └── package.json                    # Node dependencies
```

## Architecture Overview

### Multi-Frontend Architecture
```
┌─────────────────┐     ┌─────────────────┐
│  Streamlit App  │     │ Next.js + React │
│   (Original)    │     │  (Modern UI)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│        State Management Layer           │
│  ┌─────────────┐    ┌────────────────┐ │
│  │  Streamlit  │    │    Memory      │ │
│  │   Adapter   │    │   Adapter      │ │
│  └─────────────┘    └────────────────┘ │
└─────────────────┬───────────────────────┘
                  │
         ┌────────▼────────┐
         │  Service Layer  │
         │  (Stateless)    │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │   Core Logic    │
         │ (Pure Functions)│
         └─────────────────┘
```

### API Integration
- **Streamlit**: Direct service layer access with Streamlit state adapter
- **Next.js**: Communicates via FastAPI backend using memory state adapter
- **FastAPI**: Exposes core functionality as REST endpoints

## Key Commands

### Development Setup
```bash
# Backend (Python/Streamlit)
cd strava-tracks-analyzer/strava-tracks-analyzer
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Run Streamlit
streamlit run app.py

# Run FastAPI
uvicorn api.main:app --reload

# Frontend (Next.js)
cd strava-tracks-analyzer/foil-lab-web
npm install
npm run dev
```

### Testing
```bash
# Backend tests
python -m pytest tests/

# Test with coverage
python -m pytest --cov=core --cov=services --cov=utils tests/

# Frontend tests
cd foil-lab-web && npm test
```

### Deployment
```bash
# Backend API (Railway)
# Automatically deploys from main branch
# URL: https://strava-tracks-analyzer-production.up.railway.app

# Frontend (Vercel)
# Connect GitHub repo and deploy
# URL: https://foil-lab.vercel.app (when deployed)
```

## API Endpoints

### Configuration
- `GET /api/config` - Get default parameters and ranges
  ```json
  {
    "defaults": {
      "wind_direction": 90.0,
      "angle_tolerance": 25,
      "min_duration": 15,
      "min_distance": 75,
      "min_speed": 8.0
    },
    "ranges": {
      "wind_direction": {"min": 0, "max": 359, "step": 1},
      ...
    }
  }
  ```

### Track Analysis
- `POST /api/analyze-track` - Analyze GPX file
  - Form data: `file` (GPX file)
  - Query params: `wind_direction`, `angle_tolerance`, etc.
  - Returns: segments, wind estimate, performance metrics

### Health Check
- `GET /api/health` - Service health status

## State Management

### Abstract Interfaces
```python
# services/state.py
class StateService(ABC, Generic[T]):
    def get(self, key: str, default: T = None) -> T
    def set(self, key: str, value: Any) -> None
```

### Framework Adapters
- **StreamlitStateAdapter**: Wraps `st.session_state`
- **MemoryStateAdapter**: In-memory dict for API/testing

### Usage
```python
# Streamlit app
from adapters.streamlit_state import register_streamlit_adapters
register_streamlit_adapters()

# API backend
from adapters.memory_state import register_memory_adapters
register_memory_adapters()

# Services use registered adapters automatically
from services.wind_service import get_wind_service
wind_service = get_wind_service()
```

## Critical Technical Concepts

### Wind Direction
- Wind direction = where wind comes FROM (0°=N, 90°=E, 180°=S, 270°=W)
- Example: 270° wind = wind FROM the west, blowing TO the east

### Key Metrics
- **Segments**: Consistent sailing stretches with stable bearing/heading
- **Tacks**: Port (wind from left) vs Starboard (wind from right)
- **VMG**: Velocity Made Good = Speed × cos(angle to wind)
- **Angle to Wind**: Degrees off wind direction (30-50° typical upwind)

### Segment Detection Parameters
- **min_distance**: Minimum segment length (meters)
- **min_duration**: Minimum time duration (seconds)
- **angle_tolerance**: Maximum bearing variation allowed (degrees)
- **min_points**: Minimum GPS points required

## Configuration Management

### Single Source of Truth
All parameter defaults and ranges are defined in:
- `config/settings.py` - Application defaults
- `core/constants.py` - Algorithm constants

### Dynamic Configuration
- Frontend fetches configuration from `/api/config` endpoint
- Ensures consistency across all UIs
- Supports future adaptive parameters

## Development Workflow

### Feature Development
1. Implement in `core/` (pure functions, no UI dependencies)
2. Add service layer in `services/` if needed
3. Update Streamlit UI in `ui/`
4. Update API endpoints in `api/main.py`
5. Update Next.js frontend if applicable

### State Management Updates
1. Define abstract interface in `services/state.py`
2. Implement in both adapters (`streamlit_state.py`, `memory_state.py`)
3. Use dependency injection in services

### Adding New Parameters
1. Add to `config/settings.py` with `DEFAULT_` prefix
2. Update `/api/config` endpoint ranges
3. Parameters automatically flow to all frontends

## Deployment Architecture

### Production Setup
```
┌─────────────────┐         ┌─────────────────┐
│   Streamlit     │         │    Next.js      │
│  (Original UI)  │         │  (Modern UI)    │
│                 │         │   Vercel.com    │
└─────────────────┘         └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   FastAPI       │
                            │   Railway.app   │
                            │  (Python APIs)  │
                            └─────────────────┘
```

### Environment Variables
- `ANTHROPIC_API_KEY` - For AI gear comparison features
- `NEXT_PUBLIC_API_URL` - API URL for Next.js frontend

## Common Issues & Solutions

### Parameter Sync
- Always update defaults in `config/settings.py`
- Frontend fetches from API automatically
- No hardcoded values in frontends

### State Management
- Use dependency injection for services
- Register appropriate adapter at startup
- Services remain framework-agnostic

### CORS Issues
- FastAPI configured with permissive CORS for development
- Tighten for production deployment

## Recent Major Changes (June 2025)

### State Management Decoupling
- Abstracted all state operations behind interfaces
- Services no longer depend on Streamlit
- Enables multiple frontend support

### API Backend Addition
- FastAPI backend serves core algorithms
- Enables Next.js and future frontends
- Deployed on Railway

### Configuration Management
- Single source of truth for parameters
- Dynamic configuration endpoint
- Consistent defaults across all UIs

### Next.js Frontend
- Modern React-based UI
- TypeScript for type safety
- Responsive design with Tailwind CSS
- Real-time parameter adjustment

## Future Roadmap

### High Priority
- Complete Next.js feature parity
- Add polar plots and track visualization
- Implement track comparison features

### Medium Priority
- User accounts and saved sessions
- Export functionality (CSV, JSON)
- Mobile app considerations

### Low Priority
- Real-time GPS tracking
- Social features (leaderboards)
- Advanced AI analysis