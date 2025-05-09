# WingWizard Architecture

This document outlines the architecture of the WingWizard application after the refactoring.

## Directory Structure

The application is organized into the following directories:

```
strava-tracks-analyzer/
├── app.py                   # Main Streamlit entry point
├── config/                  # Configuration files
│   ├── __init__.py
│   └── settings.py          # App settings and constants
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── gpx.py               # GPX file parsing and handling
│   ├── metrics.py           # Track metrics calculations
│   ├── segments.py          # Segment detection and analysis
│   └── wind/                # Wind direction analysis
│       ├── __init__.py
│       ├── direction.py     # Wind direction estimation algorithms
│       └── models.py        # Wind data models and calculations
├── ui/                      # UI components and pages
│   ├── __init__.py
│   ├── pages/               # Main UI pages
│   │   ├── __init__.py
│   │   ├── analysis.py      # Track analysis page
│   │   ├── comparison.py    # Gear comparison page
│   │   └── guide.py         # Guide page
│   └── components/          # Reusable UI components
│       ├── __init__.py
│       ├── filters.py       # Filter UI components
│       └── visualization.py # Data visualization components
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── geo.py              # Geographic calculations
│   └── validation.py       # Input validation helpers
└── tests/                  # Test directory
    ├── __init__.py
    ├── test_gpx.py
    ├── test_metrics.py
    ├── test_segments.py
    └── test_wind.py
```

## Architecture Overview

The WingWizard application follows a clean architecture with clear separation of concerns:

1. **Core Business Logic**: The `core` directory contains all the business logic of the application, including GPX file parsing, metrics calculations, segment detection, and wind direction analysis. This logic is independent of the UI and can be reused in other contexts.

2. **UI Components**: The `ui` directory contains all the Streamlit UI components and pages. The UI is built on top of the core business logic and is responsible for presenting data to the user and handling user interactions.

3. **Configuration**: The `config` directory contains application settings and constants, centralized for easy management.

4. **Utilities**: The `utils` directory contains utility functions that are used throughout the application, such as geographic calculations and validation helpers.

5. **Tests**: The `tests` directory contains unit tests for the core business logic.

## Key Components

### Core Module

- **GPX Processing**: The `core/gpx.py` module handles GPX file parsing and processing.
- **Metrics Calculation**: The `core/metrics.py` module calculates track metrics such as distance, speed, and duration.
- **Segment Detection**: The `core/segments.py` module detects consistent segments in track data.
- **Wind Direction Estimation**: The `core/wind/direction.py` module contains algorithms for estimating wind direction based on sailing patterns.
- **Wind Models**: The `core/wind/models.py` module contains data models and structures for working with wind data.

### UI Module

- **Pages**: The `ui/pages` directory contains the main Streamlit pages of the application.
- **Components**: The `ui/components` directory contains reusable UI components such as filters and visualizations.

### Utils Module

- **Geo Calculations**: The `utils/geo.py` module contains functions for calculating geographic information such as bearings and distances.
- **Validation**: The `utils/validation.py` module contains functions for validating user input and parameters.

## Data Flow

1. The user uploads a GPX file through the Streamlit UI.
2. The GPX file is parsed into a pandas DataFrame by the GPX processing module.
3. The metrics calculation module calculates basic track metrics.
4. The segment detection module finds consistent segments in the track data.
5. The wind direction estimation module estimates the wind direction based on the segments.
6. The UI displays the results to the user, including visualizations such as the track map and polar diagram.

## Migration Guide

To migrate from the old structure to the new structure:

1. **Set up the new directory structure** as outlined above.
2. **Move the existing code** to the appropriate modules:
   - Move GPX parsing code to `core/gpx.py`
   - Move metrics calculation code to `core/metrics.py`
   - Move segment detection code to `core/segments.py`
   - Move wind direction estimation code to `core/wind/direction.py`
   - Move UI code to the appropriate files in `ui/`

3. **Update imports** in all files to reflect the new structure.
4. **Update the main app entry point** (`app.py`) to use the new structure.
5. **Run tests** to ensure the application still works as expected.

## Development Guidelines

- **Core Logic**: Focus on keeping the core business logic independent of the UI. This makes it easier to test and reuse.
- **UI Components**: Build UI components that are reusable and composable. This reduces code duplication and makes the UI more maintainable.
- **Configuration**: Use the centralized configuration system instead of hardcoding values.
- **Testing**: Write tests for the core business logic to ensure it works as expected.
- **Documentation**: Keep this document up to date as the architecture evolves.

## Future Improvements

- **Complete type hints**: Add proper type hints to all functions to improve code documentation and enable type checking.
- **Enhance error handling**: Implement more robust error handling throughout the application.
- **Expand test coverage**: Add more unit tests for the core business logic.
- **Implement advanced features**: Build on the new architecture to implement advanced features such as gear comparison and analysis.