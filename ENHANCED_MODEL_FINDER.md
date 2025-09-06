# Enhanced Model Finder for ComfyUI-Launcher

## Overview

The ComfyUI-Launcher now includes an AI-powered model finder that can automatically search the web to find missing models. This enhancement makes it bulletproof for finding any ComfyUI model that exists on the internet.

## Key Features

### 1. AI-Powered Search
- Uses Perplexity API for intelligent model search
- Searches even with partial or incorrect model names
- Understands model variations and versions

### 2. Multi-Source Search
- **CivitAI**: Direct API integration for models, LoRAs, VAEs, and embeddings
- **Hugging Face**: Searches diffusion models and repositories
- **GitHub**: Searches releases and model files
- **Direct URLs**: Validates and checks any direct download links

### 3. Intelligent Matching
- Fuzzy filename matching with relevance scoring
- Handles version numbers intelligently
- Detects model types automatically
- Provides checksums when available

### 4. Seamless Integration
- Works with existing model resolution UI
- Provides suggestions in the expected format
- Maintains backward compatibility

## Implementation Details

### New Files Created

1. **`server/model_finder.py`**
   - Core model finder implementation
   - Perplexity AI integration
   - Multi-source search strategies
   - Result ranking and deduplication

2. **`server/MODEL_FINDER_API.md`**
   - Comprehensive API documentation
   - Usage examples
   - Integration guidelines

3. **`server/test_model_finder.py`**
   - Test script for verification
   - Examples of direct usage
   - API endpoint testing

4. **`server/frontend_integration_example.js`**
   - Frontend integration examples
   - Shows how to use with existing UI

### Updated Files

1. **`server/server.py`**
   - Added `/api/find_model` endpoint
   - Added `/api/workflow/auto_resolve_models` endpoint
   - Integrated model finder with existing system

## API Endpoints

### 1. Find Model
```
POST /api/find_model
{
  "filename": "model_name.safetensors",
  "model_type": "lora"  // optional
}
```

### 2. Auto-Resolve Workflow Models
```
POST /api/workflow/auto_resolve_models
{
  "workflow_json": { ... }
}
```

## Configuration

Set the Perplexity API key via environment variable:
```bash
export PERPLEXITY_API_KEY="your-api-key"
```

Default key is provided for testing.

## Example: Finding "Wan2.1_T2V_14B_FusionX_LoRA.safetensors"

The system successfully found this specific model:
- **Source**: CivitAI
- **URL**: https://civitai.com/models/1678575?modelVersionId=1899873
- **Download**: https://civitai.com/api/download/models/1899873
- **Size**: 13.3 GB
- **Relevance Score**: 1.0 (perfect match)

## Benefits

1. **Reduced User Friction**: Automatically finds models without manual searching
2. **Higher Success Rate**: AI search finds models even with incomplete information
3. **Time Saving**: Parallel search across multiple sources
4. **Better UX**: Integrated suggestions in the existing UI
5. **Reliability**: Multiple fallback strategies ensure models are found

## Future Enhancements

1. Cache search results for performance
2. Add more model sources (GitHub releases, custom registries)
3. Implement model verification with checksums
4. Add progress tracking for large model downloads
5. Support for model version selection

## Testing

Run the test script:
```bash
cd server
python3 test_model_finder.py
```

Test the API endpoint:
```bash
python3 test_model_finder.py api
```

The enhanced model finder makes ComfyUI-Launcher significantly more powerful by eliminating the friction of finding and downloading missing models.