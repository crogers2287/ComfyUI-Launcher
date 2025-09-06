#!/bin/bash

# Enhanced build script that rebuilds frontend and restarts server
echo "🔨 Building frontend..."

cd /home/crogers2287/comfy/ComfyUI-Launcher/web
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Frontend build successful"
    
    # Get the new JS file name
    NEW_JS_FILE=$(grep 'index-.*\.js' dist/index.html | sed 's/.*src="\/assets\/\([^"]*\)".*/\1/')
    echo "📄 New JS file: $NEW_JS_FILE"
    
    # Restart server
    cd ..
    ./restart_server.sh
else
    echo "❌ Frontend build failed"
    exit 1
fi