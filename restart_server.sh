#!/bin/bash

# Script to restart the server after builds to avoid caching issues
echo "Restarting ComfyUI Launcher server..."

# Kill existing launcher processes
pkill -f "python.*server.py" || true
sleep 2

# Check if port 4000 is still in use
if lsof -i :4000 > /dev/null 2>&1; then
    echo "Port 4000 still in use, waiting..."
    sleep 3
fi

# Start the server
cd /home/crogers2287/comfy/ComfyUI-Launcher
nohup ./launcher_venv/bin/python launcher.py > server_restart.log 2>&1 &

sleep 3

# Check if server started successfully
if curl -s http://localhost:4000/ > /dev/null; then
    echo "✅ Server restarted successfully at http://localhost:4000"
    echo "Latest JS file: $(grep 'index-.*\.js' web/dist/index.html | sed 's/.*src="\/assets\/\([^"]*\)".*/\1/')"
else
    echo "❌ Server failed to start"
    tail -10 server_restart.log
fi