#!/usr/bin/env python3
"""
Run the FastAPI backend server.

Usage:
    python run_api.py
"""

import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Foil Lab API server...")
    print("📡 API will be available at: http://localhost:8000")
    print("📚 Documentation at: http://localhost:8000/docs")
    print("🛑 Press CTRL+C to stop\n")
    
    try:
        # When using reload=True, we need to pass the app as a string import path
        # instead of the actual app object
        uvicorn.run(
            "api.main:app",  # String import path instead of the app object
            host="0.0.0.0", 
            port=8000,
            reload=True  # Enable auto-reload during development
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()