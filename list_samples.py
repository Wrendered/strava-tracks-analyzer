#!/usr/bin/env python
"""
Simple script to list available sample GPX files.
"""
import os
from utils.gpx_parser import get_sample_data_paths

def main():
    sample_files = get_sample_data_paths()
    
    if not sample_files:
        print("No sample GPX files found in the data directory.")
        return
    
    print("Available sample GPX files:")
    for i, file_path in enumerate(sample_files):
        filename = os.path.basename(file_path)
        print(f"  [{i}] {filename}")
    
    print("\nTo analyze a sample file, run:")
    print("  python analyze_gpx.py --sample <index> [options]")
    print("  python analyze_gpx.py --sample <index> --visualize")
    
    print("\nTo run the Streamlit web app:")
    print("  streamlit run app.py")

if __name__ == "__main__":
    main()