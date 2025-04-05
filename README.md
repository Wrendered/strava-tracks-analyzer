# Strava Tracks Analyzer

A Streamlit application for analyzing wingfoil sessions from Strava GPX tracks. Helps analyze your sailing performance and optimize wind angles.

## Features

- Upload GPX files from Strava or other sources
- Automatically detect consistent sailing angles and segments
- Calculate optimal upwind and downwind angles
- Visualize performance with interactive maps and polar diagrams
- Optional auto-detection of wind direction based on sailing patterns
- Export analysis as CSV for further processing

## Installation

1. Clone this repository
2. Install requirements: `pip install -r requirements.txt`
3. Run the app: `streamlit run app.py`

## Usage

1. Upload a GPX file from a wingfoil session
2. Set the wind direction or use auto-detection
3. Adjust analysis parameters as needed
4. View the results and optimize your technique

## Dependencies

- streamlit
- pandas
- numpy
- gpxpy
- matplotlib
- folium
- scikit-learn
- geopy
