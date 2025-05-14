# Foil Lab Architecture

This document outlines the architecture of the Foil Lab application.

## Directory Structure

The application is organized into the following directories:

```
strava-tracks-analyzer/
├── app.py                   # Main Streamlit entry point
├── config/                  # Configuration files
│   ├── __init__.py
│   └── settings.py          # Centralized configuration and constants
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── gpx.py               # GPX file parsing and handling
│   ├── metrics.py           # Track metrics calculations
│   ├── metrics_advanced.py  # Advanced metrics algorithms
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   ├── gear_item.py     # Gear model
│   │   ├── segment.py       # Segment model
│   │   └── track.py         # Track model
│   ├── segments/            # Segment analysis
│   │   ├── __init__.py
│   │   └── analyzer.py      # Segment analyzer
│   ├── segments.py          # Segment detection
│   └── wind/                # Wind direction analysis
│       ├── __init__.py
│       ├── direction.py     # Wind direction utilities
│       ├── estimate.py      # Wind estimation
│       ├── estimator.py     # Unified wind estimator
│       └── models.py        # Wind data models
├── data/                    # Example data files
├── docs/                    # Documentation
├── services/                # Business services
│   ├── __init__.py
│   ├── segment_service.py   # Segment business logic
│   └── wind_service.py      # Wind business logic
├── tests/                   # Test cases
│   ├── __init__.py
│   ├── test_gpx.py
│   ├── test_metrics.py
│   ├── test_segments.py
│   └── test_wind.py
├── ui/                      # User interface
│   ├── __init__.py
│   ├── callbacks.py         # UI event handlers
│   ├── components/          # Reusable UI components
│   │   ├── __init__.py
│   │   ├── filters.py       # Filter UI components
│   │   ├── gear_export.py   # Gear export functionality
│   │   ├── visualization.py # Data visualization components
│   │   └── wind_ui.py       # Wind direction UI components
│   └── pages/               # Application pages
│       ├── __init__.py
│       ├── analysis.py      # Track analysis page
│       └── gear_comparison.py # Gear comparison page
└── utils/                   # Utility functions
    ├── __init__.py
    ├── analysis.py          # Analysis utilities
    ├── calculations.py      # General calculation utilities
    ├── errors.py            # Error handling framework
    ├── geo.py               # Geographic calculations
    ├── gpx_parser.py        # GPX parsing utilities
    ├── segment_analysis.py  # Segment analysis utilities
    ├── state_manager.py     # Streamlit session state management
    ├── validation.py        # Input validation helpers
    └── visualization.py     # Visualization utilities
```

## Architecture Overview

The Foil Lab application follows a clean, layered architecture with clear separation of concerns:

1. **Data Layer**: Data models and structures that represent application entities (track, segment, wind, etc.)

2. **Core Business Logic**: The `core` directory contains domain-specific algorithms and logic, independent of the UI or services.

3. **Service Layer**: The `services` directory contains business operations that coordinate between different core components and implement use cases.

4. **UI Layer**: The `ui` directory contains all Streamlit UI components, pages, and callbacks.

5. **Utility Layer**: The `utils` directory contains cross-cutting concerns and helpers.

6. **Configuration**: The `config` directory centralizes application settings and constants.

7. **Tests**: The `tests` directory contains unit and integration tests.

## Key Components

### Core Module

- **GPX Processing**: The `core/gpx.py` module handles GPX file parsing and processing.
- **Metrics Calculation**: The `core/metrics.py` and `core/metrics_advanced.py` modules calculate track metrics.
- **Segment Detection**: The `core/segments.py` module detects consistent segments in track data.
- **Segment Analysis**: The `core/segments/analyzer.py` module analyzes and filters segments.
- **Wind Estimation**: The `core/wind/estimator.py` module provides a unified wind estimation API.
- **Data Models**: The `core/models` directory contains strongly-typed data structures.

### Service Layer

- **Segment Service**: The `services/segment_service.py` module coordinates segment operations.
- **Wind Service**: The `services/wind_service.py` module coordinates wind-related operations.

### UI Module

- **Pages**: The `ui/pages` directory contains the main Streamlit pages.
- **Components**: The `ui/components` directory contains reusable UI components.
- **Callbacks**: The `ui/callbacks.py` module centralizes UI event handling.

### Utils Module

- **State Management**: The `utils/state_manager.py` module centralizes Streamlit session state.
- **Error Handling**: The `utils/errors.py` module provides standardized error handling.
- **Geo Calculations**: The `utils/geo.py` module contains geographic calculations.
- **Segment Analysis**: The `utils/segment_analysis.py` module provides utilities for segment quality analysis.

## Data Flow

1. The user uploads a GPX file through the Streamlit UI.
2. The GPX file is parsed into a pandas DataFrame by the GPX processing module.
3. The segment service detects consistent segments in the track data.
4. The wind service estimates the wind direction from the segments.
5. The segment analyzer scores and filters segments for reliability.
6. The metrics modules calculate performance metrics like VMG.
7. The UI components render visualizations and analysis.

## State Management

Streamlit's session state is centrally managed through the `utils/state_manager.py` module, which provides:

- Type-safe access to state values
- Default values for missing state
- Change tracking
- Domain-specific state managers for wind, segments, etc.

This prevents session state access from being scattered throughout the codebase.

## UI Component Design

UI components are designed with:

1. **Clear Separation**: UI components focus on presentation, not business logic.
2. **Centralized Callbacks**: Event handlers are defined in `ui/callbacks.py`.
3. **Stateless Components**: Components receive everything they need as parameters.
4. **Reusability**: Common UI elements are extracted into reusable components.

## Error Handling

Errors are handled consistently using:

1. **Custom Exceptions**: Domain-specific error types defined in `utils/errors.py`.
2. **Structured Error Details**: Errors include contextual information.
3. **Consistent Logging**: All errors are logged with appropriate levels.
4. **User-Friendly Messages**: Errors are presented to users in a helpful way.

## Development Guidelines

- **Core Logic**: Keep the core business logic independent of the UI.
- **Services**: Use services to coordinate between different core components.
- **UI Components**: Build reusable, stateless UI components.
- **Configuration**: Use the centralized configuration system.
- **State**: Use the state management utilities instead of accessing session state directly.
- **Testing**: Write tests for services and core business logic.
- **Documentation**: Keep this document up to date.

## Design Patterns Used

- **Service Pattern**: Business logic is encapsulated in service classes.
- **Strategy Pattern**: Different algorithms (e.g., wind estimation) can be selected at runtime.
- **Repository Pattern**: Data access is abstracted.
- **Factory Pattern**: Object creation is centralized.
- **Dependency Injection**: Components receive their dependencies.

## Future Improvements

- **Data Persistence**: Implement proper data storage for saving and loading analysis.
- **More Unit Tests**: Expand test coverage, especially for services.
- **API Layer**: Extract an API layer for potential backend/frontend separation.
- **Performance Optimization**: Improve performance for large datasets.
- **Documentation**: Add more developer documentation and examples.
- **Plugin System**: Support for custom analysis plugins.