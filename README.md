# Foil Lab - Wingfoil GPX Track Analyzer

A Streamlit application for analyzing wingfoil sessions from Strava GPX tracks. Helps analyze your sailing performance and optimize wind angles.

> **Note**: See [the docs directory](docs/) for detailed documentation about the application architecture and features.

## Features

### Track Analysis
- Upload GPX files from Strava or other sources
- Automatically detect consistent sailing angles and segments
- Advanced wind direction estimation with iterative refinement
- Separate port and starboard tack analysis with symmetry metrics
- Interactive maps with color-coded segments and wind arrows
- Polar performance diagrams showing speed vs angle relationships
- Distance-weighted VMG (Velocity Made Good) calculations
- Adaptive parameter scaling for long tracks to prevent over-segmentation

### Gear Comparison  
- Bulk upload and analysis of multiple tracks
- Side-by-side comparison of different gear setups
- Export individual sessions from Track Analysis page
- Unified analysis pipeline ensures consistent results
- Clean comparison table with key performance metrics
- CSV export for further analysis

### Advanced Analytics
- Quality-weighted segment detection filters GPS noise
- Wind confidence levels (High/Medium/Low/None) 
- Suspicious angle detection and filtering
- Distance-weighted performance calculations
- Real-time parameter adjustment with immediate feedback

## Recent Improvements (2024)

- **Unified Analysis Pipeline**: Created shared analysis service ensuring identical calculations between main page and bulk upload
- **Fixed VMG Discrepancy**: Resolved calculation differences between individual and bulk analysis
- **Improved Comparison Table**: Now shows metrics exactly matching the main page display
- **Removed Legacy Metrics**: Deprecated "upwind progress" in favor of sophisticated VMG calculations
- **Streamlined UI**: Removed redundant detailed comparison section for cleaner interface
- **Enhanced Wind Estimation**: Iterative algorithm refines user's initial wind estimate
- **Parameter Consistency**: Both analysis methods use identical parameters from session state

## Installation

1. Clone this repository
2. Create and activate a virtual environment:
   ```
   # Create virtual environment (already included in the repo)
   python -m venv venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```
3. Install requirements in the virtual environment: `pip install -r requirements.txt`
4. Run the app with the virtual environment activated: `streamlit run app.py`

> **Note**: Always make sure to activate the virtual environment before running the application.

## Usage

1. Upload a GPX file from a wingfoil session
2. Set the wind direction or use auto-detection
3. Adjust analysis parameters as needed
4. View the results and optimize your technique
5. Export sessions to the gear comparison page to analyze different setups

## AI-Powered Gear Comparison

The app includes AI-powered gear comparison using Claude from Anthropic:

1. Save multiple gear sessions from the Track Analysis page
2. Navigate to the Gear Comparison tab
3. Select the gear setups you want to compare
4. Click "Generate AI Analysis" to receive detailed insights

You'll need an Anthropic API key to use this feature. You can set it two ways:
- Environment variable: `export ANTHROPIC_API_KEY=your_key_here`
- Or enter it directly in the app when prompted

## Long Track Analysis

For very long tracks (3+ hours) or tracks with many tacks, the application now automatically:

1. Detects over-segmentation based on track characteristics
2. Dynamically adjusts parameters for optimal segment detection
3. Shows quality metrics and provides the ability to revert to original parameters
4. Scales min_distance, min_time, and angle_tolerance proportionally

This ensures consistent analysis quality regardless of track duration or complexity.

## Dependencies

- streamlit
- pandas
- numpy
- gpxpy
- matplotlib
- folium
- scikit-learn
- geopy
- anthropic

## Project Structure

The project follows a clean architecture with clear separation of concerns:

```
strava-tracks-analyzer/
├── app.py                        # Main Streamlit entry point
├── config/                       # Configuration files
├── core/                         # Core business logic 
│   ├── gpx.py                    # GPX file parsing
│   ├── metrics.py                # Track metrics calculations
│   ├── metrics_advanced.py       # Advanced VMG and quality calculations
│   ├── segments.py               # Segment detection and analysis
│   └── wind/                     # Wind direction analysis
├── services/                     # Business services
│   └── track_analysis_service.py # Unified analysis pipeline
├── ui/                           # UI components and pages
│   ├── pages/                    # Main UI pages
│   └── components/               # Reusable UI components
└── utils/                        # Utility functions
    └── parameter_scaling.py      # Adaptive parameter scaling
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for more details on the project structure.

## Changelog

### Version 1.2.0 (Latest)
- **MAJOR**: Created unified analysis pipeline for consistency between pages
- **FIXED**: VMG calculation discrepancy between main page and bulk upload
- **IMPROVED**: Comparison table now shows identical metrics to main page
- **REMOVED**: Deprecated "upwind progress" metric from UI
- **STREAMLINED**: Removed redundant detailed comparison section
- **ENHANCED**: Wind direction estimation with iterative refinement algorithm

### Version 1.1.0  
- **NEW**: Bulk upload functionality for gear comparison
- **IMPROVED**: Advanced wind direction estimation with confidence levels
- **ENHANCED**: Distance-weighted VMG calculations  
- **ADDED**: Adaptive parameter scaling for long tracks
- **FIXED**: Over-segmentation issues on complex tracks

### Version 1.0.0
- Initial release with basic track analysis
- GPX file upload and parsing
- Segment detection and wind angle calculations
- Interactive maps and polar diagrams
- Basic gear comparison functionality