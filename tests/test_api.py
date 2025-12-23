#!/usr/bin/env python3
"""
Test script for the FastAPI backend.

This script tests the API endpoints to ensure they're working correctly.
"""

import requests
import json
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health check endpoint."""
    response = requests.get(f"{API_BASE_URL}/api/health")
    print(f"Health check: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_root():
    """Test the root endpoint."""
    response = requests.get(f"{API_BASE_URL}/")
    print(f"Root endpoint: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200

def test_analyze_track():
    """Test the analyze track endpoint with a sample file."""
    # Find a test GPX file
    data_dir = Path("data")
    gpx_files = list(data_dir.glob("*.gpx"))
    
    if not gpx_files:
        print("No GPX files found in data directory")
        return False
    
    test_file = gpx_files[0]
    print(f"Testing with file: {test_file.name}")
    
    with open(test_file, 'rb') as f:
        files = {'file': (test_file.name, f, 'application/gpx+xml')}
        params = {
            'wind_direction': 270,
            'angle_tolerance': 25,
            'min_duration': 10,
            'min_distance': 50,
            'min_speed': 5,
            'suspicious_angle_threshold': 20
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/analyze-track",
            files=files,
            params=params
        )
    
    print(f"Analyze track: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Segments found: {len(result['segments'])}")
        print(f"Wind estimate: {result['wind_estimate']['direction']:.1f}° "
              f"(confidence: {result['wind_estimate']['confidence']})")
        print(f"VMG Upwind: {result['performance_metrics']['vmg_upwind']}")
        print("✅ Analysis successful!\n")
        return True
    else:
        print(f"Error: {response.text}\n")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Foil Lab API...\n")
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Analyze Track", test_analyze_track)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"=== {name} ===")
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"Error: {e}\n")
            results.append((name, False))
    
    print("\n=== Test Summary ===")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)