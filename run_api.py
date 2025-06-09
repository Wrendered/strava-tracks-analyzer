#!/usr/bin/env python3
"""
Run the FastAPI backend server.

Usage:
    python run_api.py
"""

import uvicorn
from api.main import app

if __name__ == "__main__":
    print("🚀 Starting Foil Lab API server...")
    print("📡 API will be available at: http://localhost:8000")
    print("📚 Documentation at: http://localhost:8000/docs")
    print("🛑 Press CTRL+C to stop\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True  # Enable auto-reload during development
    )