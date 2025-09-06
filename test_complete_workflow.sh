#!/bin/bash

echo "Testing ComfyUI Launcher Workflow Import with Auto-Resolve"
echo "=========================================================="

# The WAN workflow URL
WORKFLOW_URL="https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_wan2_2_5B_ti2v.json"

# Step 1: Fetch the workflow
echo -e "\n1. Fetching workflow from GitHub..."
WORKFLOW_JSON=$(curl -s "$WORKFLOW_URL")

# Step 2: First test import to get missing models
echo -e "\n2. Testing import to detect missing models..."
IMPORT_TEST=$(curl -s -X POST http://localhost:4000/api/import_project \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test_wan_workflow\",
    \"import_json\": $WORKFLOW_JSON,
    \"resolved_missing_models\": [],
    \"skipping_model_validation\": false
  }")

echo "Import test response:"
echo "$IMPORT_TEST" | jq '.'

# Check if we got missing models
if echo "$IMPORT_TEST" | jq -e '.error == "MISSING_MODELS"' > /dev/null; then
    echo -e "\n3. Missing models detected. Testing auto-resolve..."
    
    # Step 3: Test auto-resolve endpoint
    AUTO_RESOLVE=$(curl -s -X POST http://localhost:4000/api/workflow/auto_resolve_models \
      -H "Content-Type: application/json" \
      -d "{\"workflow_json\": $WORKFLOW_JSON}")
    
    echo "Auto-resolve response:"
    echo "$AUTO_RESOLVE" | jq '.missing_models[] | {filename: .filename, suggestions: (.ai_suggestions | length)}'
    
    # Step 4: Extract resolved models from auto-resolve response
    if echo "$AUTO_RESOLVE" | jq -e '.ai_search_enabled == true' > /dev/null; then
        echo -e "\n4. Building resolved models list from AI suggestions..."
        
        # Build resolved_missing_models array from AI suggestions
        RESOLVED_MODELS=$(echo "$AUTO_RESOLVE" | jq '[
          .missing_models[] | 
          select(.ai_suggestions | length > 0) |
          {
            filename: .filename,
            node_type: .node_type,
            dest_relative_path: .dest_relative_path,
            source: {
              type: (if .ai_suggestions[0].civitai_file_id then "civitai" else "hf" end),
              file_id: (.ai_suggestions[0].hf_file_id // .ai_suggestions[0].civitai_file_id // null),
              url: (.ai_suggestions[0].download_url // .ai_suggestions[0].url // null)
            }
          }
        ]')
        
        echo "Resolved models:"
        echo "$RESOLVED_MODELS" | jq '.'
        
        # Step 5: Try import with resolved models
        echo -e "\n5. Importing with resolved models..."
        FINAL_IMPORT=$(curl -s -X POST http://localhost:4000/api/import_project \
          -H "Content-Type: application/json" \
          -d "{
            \"name\": \"wan_auto_resolved_project\",
            \"import_json\": $WORKFLOW_JSON,
            \"resolved_missing_models\": $RESOLVED_MODELS,
            \"skipping_model_validation\": false
          }")
        
        echo "Final import response:"
        echo "$FINAL_IMPORT" | jq '.'
        
        # Check if import was successful
        if echo "$FINAL_IMPORT" | jq -e '.id' > /dev/null; then
            PROJECT_ID=$(echo "$FINAL_IMPORT" | jq -r '.id')
            echo -e "\n✅ SUCCESS! Project created with ID: $PROJECT_ID"
            
            # Check project status
            echo -e "\n6. Checking project status..."
            sleep 2
            PROJECT_STATUS=$(curl -s http://localhost:4000/api/projects)
            echo "$PROJECT_STATUS" | jq ".[] | select(.id == \"$PROJECT_ID\")"
        else
            echo -e "\n❌ FAILED! Import error:"
            echo "$FINAL_IMPORT" | jq '.error'
        fi
    else
        echo -e "\n❌ Auto-resolve failed to find suggestions"
    fi
else
    echo -e "\n✅ No missing models or import succeeded directly"
fi