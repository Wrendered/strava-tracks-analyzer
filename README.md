# Strava Tracks Analyzer

A Streamlit application for analyzing wingfoil sessions from Strava GPX tracks. Helps analyze your sailing performance and optimize wind angles.

## Features

- Upload GPX files from Strava or other sources
- Automatically detect consistent sailing angles and segments
- Calculate optimal upwind and downwind angles
- Visualize performance with interactive maps and polar diagrams
- Optional auto-detection of wind direction based on sailing patterns
- Compare different gear setups (board, foil, wing combinations)
- AI-powered gear comparison analysis with Claude
- Export analysis as CSV for further processing
- Bulk upload and analysis of multiple tracks

## Installation

1. Clone this repository
2. Install requirements: `pip install -r requirements.txt`
3. Run the app: `streamlit run app.py`

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
