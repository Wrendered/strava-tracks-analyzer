# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Foil Lab** (formerly WingWizard) is a Streamlit-based web application for analyzing wingfoiling and sailing GPS tracks from Strava. It helps windsurfers optimize performance by detecting sailing segments, estimating wind direction, calculating VMG, and comparing gear setups using AI.

## Key Commands

### Development Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_wind_algorithm.py

# Run with coverage
python -m pytest --cov=core --cov=services --cov=utils tests/

# Test data available in data/ directory:
# - test_file_270_degrees.gpx (for over-segmentation testing)
# - test_file_short_tacks_*.gpx (for short tack handling)
```

### Linting and Type Checking
```bash
# Currently no linting/type checking configured
# Consider adding: pylint, flake8, mypy, or ruff
```

## Architecture Overview

The project follows a clean, layered architecture:

### Core Business Logic (`core/`)
- **models/** - Domain models (Track, Segment, GearItem)
- **gpx.py** - GPX file parsing and track data extraction
- **metrics.py** - Basic performance calculations (speed, VMG, angles)
- **metrics_advanced.py** - Complex metrics and wind estimation algorithms
- **segments/** - Segment detection and analysis
- **wind/** - Wind direction estimation strategies (basic, iterative, weighted)

### Service Layer (`services/`)
- **SegmentService** - Coordinates segment operations, tightly coupled to StateManager
- **WindService** - Manages wind estimation, also coupled to state management

### UI Layer (`ui/`)
- **pages/** - Main application pages (analysis.py, gear_comparison.py)
- **components/** - Reusable UI elements
- **callbacks.py** - Centralized event handling (getting large and complex)

### Utilities (`utils/`)
- **state_manager.py** - Centralized Streamlit session state (creates coupling)
- **analysis.py** - Mixed responsibilities (300+ line functions, should be split)
- **calculations.py** - Geographic and sailing calculations

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
- **min_distance**: Minimum segment length (adaptive scaling)
- **min_duration**: Minimum time duration (adaptive scaling)
- **angle_threshold**: Maximum bearing variation allowed
- **min_points**: Minimum GPS points required

## Key Algorithms

### Wind Direction Estimation
1. Starts with user input as anchor point
2. Balances port/starboard tack angles
3. Filters impossible angles (<20° to wind)
4. Provides confidence levels (High/Medium/Low/None)
5. Three methods: basic, iterative, weighted

### Adaptive Parameter Scaling
For tracks >3 hours:
- distance_factor = 1 + (track_hours - 3) * 0.25
- time_factor = 1 + (track_hours - 3) * 0.2
- Scales min_distance and min_duration accordingly

### VMG Calculation
- Distance-weighted averaging across segments
- Filters segments within 20° of best upwind angle
- Separate calculations for upwind/downwind

## Known Issues & Solutions

### Code Quality Issues
- **Long functions**: `estimate_wind_direction()` in utils/analysis.py is 300+ lines
- **Magic numbers**: 15°, 60°, 0.25 scattered without constants
- **Circular imports**: Between wind and segment modules
- **Pandas warnings**: Use `.copy()` to avoid SettingWithCopyWarning
- **Missing abstractions**: No interface for wind estimation strategies

### Common Problems
- **Over-segmentation**: Use adaptive parameter scaling for long tracks
- **Incorrect wind**: Check for unrealistic pointing angles (<20°)
- **Short tacks bias**: Apply distance weighting in calculations
- **State coupling**: Services directly access Streamlit session state

## Environment Variables
- `ANTHROPIC_API_KEY` - Required for AI gear comparison features

## Key Dependencies
- streamlit (1.44.1) - UI framework
- pandas/numpy - Data processing
- gpxpy - GPX parsing
- folium - Interactive maps
- anthropic - Claude API for gear analysis

## Recent Refactoring

### State Management Decoupling (June 2025)
- **NEW**: Abstract state management interfaces in `services/state.py`
- **NEW**: Framework adapters in `adapters/` (Streamlit, memory-based)
- **NEW**: Dependency injection for all state operations
- **UPDATED**: `services/wind_service.py` now uses injected state dependencies
- **BENEFIT**: 85% of codebase now framework-agnostic, ready for UI migration

### Track Analysis Service (2024)
- Created `services/track_analysis_service.py` for unified analysis pipeline
- Both main page and bulk upload now use identical analysis code
- Fixed VMG calculation discrepancy between pages
- Eliminated duplicate segment detection and wind estimation logic

### Analysis Pipeline Consistency
- `analyze_track_file()` - Single source of truth for file analysis
- `TrackAnalysisResult` - Consistent result container
- `create_gear_item_from_analysis()` - Standard gear item creation
- Both pages use `get_analysis_parameters_from_session()` for same parameters

### Deprecated Metrics
- `upwind_progress_speed` - Legacy simple calculation (avg_speed × cos(avg_angle))
- Replaced by `vmg_upwind` - Sophisticated distance-weighted algorithm
- Kept in GearItem model for backward compatibility but removed from UI

## Architecture Overview (Updated June 2025)

The project now follows a clean, framework-agnostic architecture:

### State Management Layer (`services/state.py`, `adapters/`)
- **Abstract interfaces**: `StateService`, `WindStateService`, `SegmentStateService`
- **Framework adapters**: Streamlit (`adapters/streamlit_state.py`), Memory (`adapters/memory_state.py`)
- **Dependency injection**: `StateServiceRegistry` manages service implementations
- **Easy migration**: Switch frameworks by changing adapter registration

### Example Usage
```python
# Framework-agnostic service
from services.wind_service import get_wind_service
wind_service = get_wind_service()  # Uses registered adapter

# Or with explicit injection
from adapters.memory_state import register_memory_adapters
register_memory_adapters()  # For testing/CLI
```

## Development Priorities

### High Priority
- ✅ **COMPLETED**: State management decoupling for framework independence
- Refactor segment_service.py to use dependency injection
- Extract magic numbers to constants
- Improve wind direction with segment quality weighting

### Medium Priority
- Add jibing/tacking event detection
- Implement track comparison features
- ✅ **COMPLETED**: Decouple services from UI state

### Low Priority
- Mobile experience optimization
- Tutorial/onboarding flow
- Performance caching for expensive calculations