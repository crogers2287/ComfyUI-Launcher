/**
 * Frontend Integration Example for Enhanced Model Finder
 * This shows how to integrate the AI-powered model finder with the existing UI
 */

// Example 1: Find a specific model
async function findModel(filename) {
    try {
        const response = await fetch('/api/find_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: filename,
                model_type: null // Optional, can be 'checkpoint', 'lora', 'vae', etc.
            })
        });

        const data = await response.json();
        
        if (data.success) {
            console.log(`Found ${data.results.length} results for ${filename}`);
            
            // Display results in UI
            data.results.forEach((result, index) => {
                console.log(`${index + 1}. ${result.filename}`);
                console.log(`   Source: ${result.source}`);
                console.log(`   Download: ${result.download_url}`);
                console.log(`   Relevance: ${result.relevance_score}`);
            });
            
            return data.results;
        } else {
            console.error('Error:', data.error);
            return [];
        }
    } catch (error) {
        console.error('Failed to find model:', error);
        return [];
    }
}

// Example 2: Auto-resolve all missing models in a workflow
async function autoResolveWorkflowModels(workflowJson) {
    try {
        const response = await fetch('/api/workflow/auto_resolve_models', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                workflow_json: workflowJson
            })
        });

        const data = await response.json();
        
        if (data.error === 'MISSING_MODELS' && data.ai_search_enabled) {
            console.log('Found missing models with AI suggestions:');
            
            data.missing_models.forEach(model => {
                console.log(`\nMissing: ${model.filename}`);
                console.log('AI Suggestions:');
                
                model.ai_suggestions.forEach((suggestion, index) => {
                    console.log(`  ${index + 1}. ${suggestion.filename}`);
                    console.log(`     Source: ${suggestion.source}`);
                    console.log(`     Download: ${suggestion.download_url}`);
                    console.log(`     Score: ${suggestion.relevance_score}`);
                });
            });
            
            return data;
        }
        
        return data;
    } catch (error) {
        console.error('Failed to auto-resolve models:', error);
        throw error;
    }
}

// Example 3: Enhanced MissingModelItem component integration
// This would replace or enhance the existing resolution logic
async function enhanceMissingModelSuggestions(missingModel) {
    // First try the AI-powered finder
    const aiResults = await findModel(missingModel.filename);
    
    if (aiResults.length > 0) {
        // Convert AI results to the format expected by MissingModelItem
        const suggestions = aiResults.slice(0, 5).map(result => ({
            filename: result.filename,
            source: result.source,
            url: result.url,
            download_url: result.download_url,
            node_type: result.model_type || missingModel.node_type,
            sha256_checksum: result.sha256_checksum,
            // Map to the expected ID format
            civitai_file_id: result.source === 'civitai' ? result.metadata.file_id : null,
            hf_file_id: result.source === 'huggingface' ? result.metadata.path : null
        }));
        
        // Merge with existing suggestions
        return [...suggestions, ...missingModel.suggestions];
    }
    
    return missingModel.suggestions;
}

// Example 4: Resolve a model with the found result
async function resolveModelWithAISuggestion(missingModel, suggestion) {
    // Use the existing resolution mutation
    const resolveData = {
        filename: missingModel.filename,
        node_type: missingModel.node_type,
        dest_relative_path: missingModel.dest_relative_path,
        source: {
            type: suggestion.source === 'civitai' ? 'civitai' : 
                  suggestion.source === 'huggingface' ? 'hf' : 'url',
            file_id: suggestion.civitai_file_id || suggestion.hf_file_id,
            url: suggestion.download_url
        }
    };
    
    // Call the existing resolve mutation
    return await resolveMutation.mutateAsync(resolveData);
}

// Example usage
(async () => {
    // Test finding a specific model
    console.log('=== Testing Model Finder ===');
    const results = await findModel('Wan2.1_T2V_14B_FusionX_LoRA.safetensors');
    
    // Test auto-resolving workflow
    console.log('\n=== Testing Workflow Auto-Resolution ===');
    const workflowJson = { /* your workflow JSON */ };
    const resolvedWorkflow = await autoResolveWorkflowModels(workflowJson);
})();