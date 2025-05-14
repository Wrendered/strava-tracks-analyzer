# Strava Tracks Analyzer Refactoring Plan

## Overview

This document outlines a comprehensive refactoring plan for the Strava Tracks Analyzer application. The goal is to improve code maintainability, readability, testability, and extensibility while preserving all existing functionality.

## Key Areas for Improvement

### 1. Centralized State Management

**Current Issue:** The application relies heavily on Streamlit's session state, with state management spread across multiple files. This makes it difficult to track state changes and dependencies.

**Proposed Solution:**
- Create a dedicated `StateManager` class that encapsulates session state operations
- Implement getter/setter methods with proper typing
- Centralize state initialization logic
- Provide hooks for state change notifications

**Files to Modify:**
- Create new: `utils/state_manager.py`
- Modify: `ui/pages/analysis.py`, `ui/components/wind_ui.py`

### 2. Separation of UI and Business Logic

**Current Issue:** Business logic is mixed with UI code, particularly in the analysis page, making the code harder to test and maintain.

**Proposed Solution:**
- Extract calculation logic from UI components into dedicated service modules
- Implement a cleaner service-based architecture
- Make UI components focus purely on presentation
- Improve the testability of business logic

**Files to Modify:**
- Create new: `services/segment_service.py`, `services/wind_service.py`
- Modify: `ui/pages/analysis.py`, `ui/components/wind_ui.py`

### 3. Unified Wind Calculation API

**Current Issue:** The codebase has two parallel wind estimation methods (`estimate_wind_direction` and `estimate_wind_direction_weighted`), causing confusion about which one to use.

**Proposed Solution:**
- Create a unified `WindEstimator` class with configurable algorithms
- Deprecate redundant functions and consolidate options
- Provide a clear, consistent API for wind estimation
- Add strategy pattern for pluggable estimation algorithms

**Files to Modify:**
- Create new: `core/wind/estimator.py`
- Modify: `core/wind/estimate.py`, `core/metrics_advanced.py`

### 4. Enhanced Segment Analysis

**Current Issue:** Segment filtering, scoring, and analysis logic is scattered across multiple files, leading to inconsistent handling.

**Proposed Solution:**
- Create a dedicated `SegmentAnalyzer` class
- Centralize segment quality scoring logic
- Implement flexible filtering strategies
- Add methods for segment comparison and grouping

**Files to Modify:**
- Create new: `core/segments/analyzer.py`
- Modify: `core/segments.py`, `utils/segment_analysis.py`

### 5. Improved Callback Handling

**Current Issue:** UI callbacks are defined inline, making them difficult to test and reuse.

**Proposed Solution:**
- Extract callbacks to standalone, testable functions
- Implement a consistent callback registration pattern
- Add better typing for callbacks
- Improve error handling in callbacks

**Files to Modify:**
- Create new: `ui/callbacks.py`
- Modify: `ui/pages/analysis.py`, `ui/components/wind_ui.py`

### 6. Centralized Configuration

**Current Issue:** Configuration parameters are spread across multiple files, making it difficult to track and update defaults.

**Proposed Solution:**
- Move all configuration to the central config module
- Create specific configuration classes for different subsystems
- Add validation for configuration parameters
- Provide documentation for each configuration option

**Files to Modify:**
- Modify: `config/settings.py`
- Update references in multiple files

### 7. Stronger Data Models

**Current Issue:** The application passes around pandas DataFrames with implicit column requirements, leading to brittle code.

**Proposed Solution:**
- Create explicit data classes for core domain objects
- Add validation for data models
- Implement conversion methods between DataFrames and domain objects
- Add serialization/deserialization support

**Files to Modify:**
- Create new: `core/models/segment.py`, `core/models/track.py`
- Modify: Multiple files that use these data structures

### 8. Enhanced Error Handling

**Current Issue:** Error handling is inconsistent throughout the codebase.

**Proposed Solution:**
- Create a custom error hierarchy
- Implement consistent error handling patterns
- Add user-friendly error messages
- Improve logging of errors

**Files to Modify:**
- Create new: `utils/errors.py`
- Modify: Multiple files to use new error handling

### 9. Improved Documentation

**Current Issue:** While function docstrings exist, documentation of core domain concepts is limited.

**Proposed Solution:**
- Add domain-focused documentation explaining key concepts
- Create more comprehensive API documentation
- Add usage examples and tutorials
- Improve inline comments for complex logic

**Files to Modify:**
- Create new: `docs/domain-concepts.md`, `docs/api-reference.md`
- Update docstrings in multiple files

## Implementation Plan

The refactoring will be implemented in the following phases:

### Phase 1: Foundation
1. Create State Management module
2. Implement core data models
3. Set up error handling framework
4. Centralize configuration

### Phase 2: Core Logic Refactoring
1. Create unified wind estimation API
2. Implement segment analyzer
3. Extract business logic from UI components

### Phase 3: UI Improvements
1. Refactor UI components to use new services
2. Implement callback improvements
3. Enhance error visualization

### Phase 4: Documentation and Testing
1. Add comprehensive unit tests
2. Improve documentation
3. Create usage examples

## Testing Strategy

Each refactoring step will include:
1. Unit tests for new functionality
2. Integration tests to ensure compatibility with existing code
3. UI tests to verify behavior remains unchanged

## Rollout Plan

To minimize disruption, the refactoring will be rolled out incrementally:
1. Deploy foundation changes first
2. Gradually replace core components
3. Update UI components last
4. Maintain backward compatibility throughout

## Success Metrics

The refactoring will be considered successful if:
1. Code maintainability metrics improve (cyclomatic complexity, coupling)
2. Test coverage increases
3. No regressions in functionality
4. Development velocity increases for future features