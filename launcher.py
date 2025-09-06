#!/usr/bin/env python3
"""Main launcher entry point for ComfyUI-Launcher."""
import sys
import os

# Add backend to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from backend.src.server import app

if __name__ == "__main__":
    # Import after path setup
    from server import socketio
    
    print("Starting ComfyUI Launcher...")
    print("Open http://localhost:4000 in your browser.")
    
    # Run with SocketIO
    socketio.run(
        app,
        host="0.0.0.0",
        port=4000,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )