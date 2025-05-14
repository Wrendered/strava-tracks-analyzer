# Foil Lab - Wingfoil GPX Track Analyzer

A Streamlit application for analyzing wingfoil sessions from Strava GPX tracks. Helps analyze your sailing performance and optimize wind angles.

> **Note**: See [the docs directory](docs/) for detailed documentation about the application architecture and features.

## Features

- Upload GPX files from Strava or other sources
- Automatically detect consistent sailing angles and segments
- Calculate optimal upwind and downwind angles
- Visualize performance with interactive maps and polar diagrams
- Advanced wind direction estimation with confidence levels
- Separate port and starboard tack analysis
- Compare different gear setups (board, foil, wing combinations)
- AI-powered gear comparison analysis with Claude
- Export analysis as CSV for further processing
- Bulk upload and analysis of multiple tracks
- Adaptive parameter scaling for long tracks (NEW!)

## Recent Improvements

- **Automatic Parameter Scaling**: The app now automatically optimizes segmentation parameters for long tracks to prevent over-segmentation
- **Track Segmentation**: Enhanced segment detection with adaptive parameters for different track types
- **Wind Direction UI**: Improved wind direction selection with visual feedback
- **Performance Analysis**: Better analytics for upwind and downwind performance

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
├── app.py                   # Main Streamlit entry point
├── config/                  # Configuration files
├── core/                    # Core business logic 
│   ├── gpx.py               # GPX file parsing
│   ├── metrics.py           # Track metrics calculations
│   ├── segments.py          # Segment detection and analysis
│   └── wind/                # Wind direction analysis
├── ui/                      # UI components and pages
│   ├── pages/               # Main UI pages
│   └── components/          # Reusable UI components
└── utils/                   # Utility functions
    └── parameter_scaling.py # Adaptive parameter scaling
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for more details on the project structure.