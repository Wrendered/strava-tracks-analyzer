# WingWizard - Refactoring Project Plan

## Project Overview

WingWizard is a Streamlit application for analyzing wingfoil sessions from Strava GPX tracks. This refactoring project aims to improve code organization, maintainability, and extensibility while enhancing user experience and adding new features.

## Completed Work (✅)

### 1. Directory Structure Reorganization (✅ Completed)
- **Priority**: High
- **Status**: Completed
- **Description**: Implemented a clean, maintainable directory structure with clear separation of concerns
  - Created `config/` for application settings
  - Created `core/` for business logic (gpx, metrics, segments, wind)
  - Created `ui/` for UI components and pages
  - Maintained `utils/` for utility functions
  - Added `tests/` for test cases

### 2. Wind Direction Estimation Improvement (✅ Completed)
- **Priority**: High
- **Status**: Completed
- **Description**: Enhanced wind direction estimation algorithms
  - Created a unified API with `WindEstimate` model
  - Added confidence levels to estimation results
  - Implemented proper error handling and fallbacks
  - Added detailed logging for better debugging

### 3. Navigation and UI Framework (✅ Completed)
- **Priority**: Medium
- **Status**: Completed
- **Description**: Improved application navigation and UI structure
  - Simplified page navigation
  - Created dedicated UI components for common elements
  - Fixed navigation issues with feature modules

### 4. Visualization Enhancements (✅ Completed)
- **Priority**: Medium
- **Status**: Completed
- **Description**: Fixed and enhanced data visualizations
  - Fixed map zoom level to properly center on the track
  - Fixed polar plot orientation to correctly display port and starboard tacks
  - Improved data representation and axis limits

### 5. Metrics Calculation (✅ Completed)
- **Priority**: Medium
- **Status**: Completed
- **Description**: Improved metrics calculation and display
  - Added Upwind Progress Speed metric for better distance estimation
  - Improved average angle calculations
  - Enhanced display of tack-specific statistics

## In-Progress Work (🔄)

### 1. UI Component Modularity (🔄 In Progress)
- **Priority**: High
- **Status**: In Progress
- **Description**: Breaking down UI into reusable components
  - Created `wind_ui.py` with dedicated wind direction components
  - Working on extracting other common UI patterns into components
  - Need to ensure consistent styling and interaction patterns

### 2. Algorithm Testing and Validation (🔄 In Progress)
- **Priority**: Medium
- **Status**: In Progress
- **Description**: Extensive testing of wind direction algorithms
  - Created test files with known wind directions
  - Testing with various file formats and edge cases
  - Validating estimation results against expected outcomes

## Pending Work (⏳)

### 1. Wind Direction Slider Fix (⏳ Pending)
- **Priority**: High
- **Status**: Pending
- **Description**: Fix the wind direction slider to prevent automatic recalculation
  - The slider is currently recalculating when released rather than waiting for the "Apply" button
  - Need to modify the `wind_direction_selector` component to only trigger calculations on button click
  - Ensure session state is properly maintained during slider interaction

### 2. Documentation Improvements (⏳ Pending)
- **Priority**: Medium
- **Status**: Pending
- **Description**: Enhance code documentation and user guides
  - Add comprehensive docstrings to all functions
  - Create user documentation explaining wind direction concepts
  - Add examples of different sailing patterns and their analysis

### 3. Error Handling Standardization (⏳ Pending)
- **Priority**: Medium
- **Status**: Pending
- **Description**: Implement consistent error handling across all modules
  - Create a centralized error handling system
  - Add user-friendly error messages for common issues
  - Improve logging for debugging purposes

### 4. Type Annotations (⏳ Pending)
- **Priority**: Low
- **Status**: Pending
- **Description**: Add type annotations to all functions
  - Ensure consistent type usage across the codebase
  - Add mypy configuration for type checking
  - Fix any type-related issues

## Future Enhancements (🔮)

### 1. Data Export Functionality
- **Priority**: Medium
- **Status**: Future
- **Description**: Allow users to export analysis results
  - Add CSV export for segment data
  - Add image export for visualizations
  - Add PDF report generation option

### 2. Multi-Track Comparison
- **Priority**: Medium
- **Status**: Future
- **Description**: Enable comparison between multiple tracks
  - Compare performance across sessions
  - Track improvement over time
  - Compare different gear setups

### 3. User Profiles and Preferences
- **Priority**: Low
- **Status**: Future
- **Description**: Add user profiles to store preferences
  - Save preferred analysis parameters
  - Track favorite locations
  - Store gear information

## Testing Requirements

Before considering the refactoring complete, the following test cases must pass:

1. **File Format Tests**
   - Standard GPX files with complete metadata
   - GPX files with missing time data
   - GPS files with non-standard tags (Strava format)
   - Large GPX files (performance test)

2. **Wind Direction Tests**
   - Tracks with known wind directions (0°, 90°, 180°, 270°)
   - Tracks with mixed upwind/downwind patterns
   - Tracks with predominately one tack
   - Edge cases with suspicious angles

3. **UI Interaction Tests**
   - Wind direction selector works correctly
   - Segment selection filters apply properly
   - Map and polar plot update with changes
   - All buttons and controls function as expected

## Release Plan

1. **Alpha Release (Completed)**
   - Basic functionality working
   - Core algorithms implemented
   - Simple UI in place

2. **Beta Release (Current)**
   - Refactored codebase
   - Enhanced UI components
   - Improved algorithms
   - Fixed critical bugs

3. **Release Candidate**
   - All planned features implemented
   - All UI components finalized
   - Comprehensive testing completed
   - Documentation finished

4. **Version 1.0**
   - Production-ready release
   - All known bugs fixed
   - Performance optimized
   - User documentation complete

## Notes

- The wind direction slider issue is a key UX problem that needs to be fixed before the release candidate
- All UI components should follow a consistent style and interaction pattern
- Performance should be regularly tested with large GPX files