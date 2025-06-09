# Foil Lab Architecture

## System Overview

Foil Lab is a multi-frontend application for analyzing wingfoil/sailing GPS tracks. The architecture emphasizes code reuse, clean separation of concerns, and support for multiple UI frameworks.

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                           │
├────────────────────────┬────────────────────────┬────────────────────┤
│    Streamlit App       │    Next.js + React     │   Future UIs       │
│  (Original Python UI)  │    (Modern Web UI)     │  (Mobile/Desktop)  │
└───────────┬────────────┴───────────┬────────────┴────────────────────┘
            │                        │
            │ Direct                 │ HTTPS/REST
            │ Service               │
            │ Access                ▼
            │              ┌─────────────────────┐
            │              │   FastAPI Backend   │
            │              │   (REST API)        │
            │              └──────────┬──────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      State Management Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Streamlit State  │  │  Memory State    │  │  Redis State    │  │
│  │    Adapter       │  │    Adapter       │  │   (Future)      │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Service Layer                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Track Analysis  │  │  Wind Service    │  │ Segment Service │  │
│  │     Service      │  │                  │  │                 │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Core Business Logic                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   GPX Parser     │  │ Segment Detector │  │ Wind Estimator  │  │
│  │                  │  │                  │  │                 │  │
│  ├──────────────────┤  ├──────────────────┤  ├─────────────────┤  │
│  │ Metrics Calculator│  │ Angle Calculator │  │ VMG Calculator  │  │
│  │                  │  │                  │  │                 │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
📁 strava-tracks-analyzer/              # Parent directory
├── 📁 strava-tracks-analyzer/          # Backend + Streamlit
│   ├── api/                            # FastAPI REST backend
│   ├── core/                           # Framework-agnostic algorithms
│   ├── services/                       # State management & orchestration
│   ├── adapters/                       # Framework adapters
│   ├── ui/                             # Streamlit UI
│   ├── config/                         # Configuration
│   ├── docs/                           # Documentation
│   └── tests/                          # Test suite
│
└── 📁 foil-lab-web/                    # Next.js frontend (separate repo)
    ├── app/                            # Next.js pages
    ├── components/                     # React components
    └── lib/                            # API client
```

## Data Flow

### Track Analysis Pipeline
```
GPX File Upload
      │
      ▼
GPX Parser (core/gpx.py)
      │
      ▼
Track Object Creation
      │
      ▼
Segment Detection (core/segments/)
      │
      ▼
Wind Estimation (core/wind/)
      │
      ▼
Performance Metrics (core/metrics.py)
      │
      ▼
Results Display
```

### State Management Flow
```
UI Component
      │
      ▼
Service Layer Request
      │
      ▼
StateServiceRegistry
      │
      ▼
Appropriate Adapter (Streamlit/Memory)
      │
      ▼
State Storage (Session/Memory)
```

## Key Design Principles

1. **Framework Independence**: Core algorithms work with any UI
2. **Single Source of Truth**: Configuration managed centrally
3. **Dependency Injection**: Services use abstract state interfaces
4. **Clean Architecture**: Clear separation between layers
5. **API-First**: REST API enables multiple frontends

## Deployment Strategy

```
Production:
┌─────────────────┐         ┌─────────────────┐
│   Streamlit     │         │    Next.js      │
│  (Optional)     │         │   Vercel.com    │
│                 │         │                 │
└─────────────────┘         └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   FastAPI       │
                            │   Railway.app   │
                            │                 │
                            └─────────────────┘
```

This architecture enables:
- **Multiple UIs** from the same codebase
- **Independent deployment** of components
- **Easy testing** with isolated layers
- **Future scalability** with stateless design