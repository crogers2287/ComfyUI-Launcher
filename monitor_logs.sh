#!/bin/bash

echo "Monitoring ComfyUI Launcher logs for imports..."
echo "Press Ctrl+C to stop"
echo "===================="

# Monitor multiple log files
tail -f server_restart.log install.log 2>/dev/null | while read line; do
    # Highlight errors in red
    if echo "$line" | grep -qE "(ERROR|error|Error|Failed|failed|Exception|Traceback|500 -|400 -)"; then
        echo -e "\033[31m$line\033[0m"
    # Highlight import requests in yellow
    elif echo "$line" | grep -qE "(import_project|workflow/validate|missing_models)"; then
        echo -e "\033[33m$line\033[0m"
    # Highlight success in green
    elif echo "$line" | grep -qE "(200 -|success|Success|completed)"; then
        echo -e "\033[32m$line\033[0m"
    else
        echo "$line"
    fi
done