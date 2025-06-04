# Foil Lab Cleanup Plan

## Overview
This document outlines the comprehensive cleanup and refactoring plan for the Foil Lab (Strava Tracks Analyzer) codebase.

## Phase 1: Extract Constants and Magic Numbers ✅
1. Create `core/constants.py` for all magic numbers
2. Replace all hard-coded values throughout the codebase
3. Document what each constant represents

## Phase 2: Break Down Complex Functions
1. Refactor `utils/analysis.py::estimate_wind_direction()` (302 lines)
   - Extract basic method to separate function
   - Extract iterative method to separate function
   - Extract weighted method to separate function
   - Create main orchestrator function
2. Refactor `core/metrics_advanced.py::estimate_wind_direction_weighted()` (208 lines)
   - Break into smaller calculation functions
   - Separate validation from calculation
3. Refactor `utils/analysis.py::find_consistent_angle_stretches()` (103 lines)
   - Extract segment validation logic
   - Separate clustering from filtering

## Phase 3: Fix Architecture Issues
1. Resolve circular dependencies
   - Create `core/interfaces.py` for shared types
   - Move shared utilities to dedicated modules
   - Refactor imports to avoid circular references
2. Create abstraction layer for UI
   - Create `core/state_interface.py` 
   - Implement state adapter pattern
   - Remove direct Streamlit dependencies from core

## Phase 4: Eliminate Code Duplication
1. Create `core/calculations.py` for shared calculations
   - Consolidate VMG calculations
   - Unify wind conversion functions
   - Centralize bearing/angle calculations
2. Create `core/analysis_patterns.py` for common patterns
   - Port/starboard analysis
   - Segment quality scoring
   - Performance metrics

## Phase 5: Add Type Safety and Error Handling
1. Add type hints to all functions
2. Create custom exceptions in `utils/errors.py`
3. Replace generic exception catching
4. Add input validation for all public functions

## Phase 6: Testing and Quality
1. Add unit tests for refactored functions
2. Add integration tests for key workflows
3. Set up linting (ruff) and type checking (mypy)
4. Add pre-commit hooks

## Phase 7: Performance Optimization
1. Implement caching for expensive calculations
2. Optimize DataFrame operations
3. Add progress indicators for long operations

## Execution Order
1. Constants extraction (lowest risk, immediate benefit)
2. Function breakdown (improves readability)
3. Architecture fixes (enables better testing)
4. Code deduplication (reduces maintenance)
5. Type safety (catches bugs)
6. Testing (ensures quality)
7. Performance (enhances user experience)

## Success Metrics
- No functions > 50 lines
- No magic numbers in code
- 80%+ test coverage on core modules
- All functions have type hints
- No circular imports
- Clean linting and type checking output