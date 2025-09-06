# Model Finder API Documentation

The ComfyUI-Launcher now includes an enhanced AI-powered model finder that can automatically search for missing models across multiple sources including CivitAI, Hugging Face, and GitHub.

## Configuration

The model finder uses the Perplexity API for intelligent search. You can configure the API key via environment variable:

```bash
export PERPLEXITY_API_KEY="your-api-key-here"
```

Default API key is provided but should be replaced for production use.

## API Endpoints

### 1. Find Model

Find a specific model by filename.

**Endpoint:** `POST /api/find_model`

**Request Body:**
```json
{
  "filename": "Wan2.1_T2V_14B_FusionX_LoRA.safetensors",
  "model_type": "lora"  // optional: checkpoint, lora, vae, controlnet, etc.
}
```

**Response:**
```json
{
  "success": true,
  "query": "Wan2.1_T2V_14B_FusionX_LoRA.safetensors",
  "results": [
    {
      "filename": "Wan2.1_T2V_14B_FusionX_LoRA.safetensors",
      "source": "civitai",
      "url": "https://civitai.com/models/12345",
      "download_url": "https://civitai.com/api/download/models/12345",
      "file_size": 147456000,
      "sha256_checksum": "abc123...",
      "description": "High quality LoRA model...",
      "model_type": "lora",
      "relevance_score": 0.95,
      "metadata": {
        "model_id": 12345,
        "version_id": 67890
      }
    }
  ]
}
```

### 2. Auto-Resolve Workflow Models

Automatically find and suggest resolutions for all missing models in a workflow.

**Endpoint:** `POST /api/workflow/auto_resolve_models`

**Request Body:**
```json
{
  "workflow_json": {
    // Your ComfyUI workflow JSON
  }
}
```

**Response:**
```json
{
  "success": false,
  "error": "MISSING_MODELS",
  "ai_search_enabled": true,
  "missing_models": [
    {
      "filename": "model.safetensors",
      "node_type": "CheckpointLoaderSimple",
      "dest_relative_path": "checkpoints",
      "ai_suggestions": [
        {
          "filename": "model_v1.safetensors",
          "source": "huggingface",
          "url": "https://huggingface.co/org/model",
          "download_url": "https://huggingface.co/org/model/resolve/main/model_v1.safetensors",
          "node_type": "checkpoint",
          "sha256_checksum": "def456...",
          "relevance_score": 0.92,
          "hf_file_id": "model_v1.safetensors"
        }
      ]
    }
  ]
}
```

## Features

### 1. Multi-Source Search
- **CivitAI**: Searches models, LoRAs, VAEs, and embeddings
- **Hugging Face**: Searches diffusion models and repositories
- **GitHub**: Searches releases and model files
- **Direct URLs**: Validates and checks direct download links

### 2. Intelligent Matching
- Fuzzy filename matching
- Version number handling
- Model type detection
- Relevance scoring

### 3. AI-Powered Search
- Uses Perplexity AI to find models even with partial or incorrect names
- Searches documentation and model cards
- Extracts download URLs, checksums, and metadata

### 4. Integration with Existing System
- Seamlessly integrates with the existing model resolution UI
- Provides suggestions in the same format as the original system
- Maintains compatibility with manual URL imports

## Usage Examples

### Python Example
```python
import requests

# Find a specific model
response = requests.post(
    "http://localhost:5000/api/find_model",
    json={
        "filename": "sd_xl_base_1.0.safetensors",
        "model_type": "checkpoint"
    }
)
results = response.json()["results"]
```

### JavaScript Example
```javascript
// Auto-resolve all missing models in a workflow
const response = await fetch('/api/workflow/auto_resolve_models', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ workflow_json: workflowData })
});

const data = await response.json();
if (data.error === 'MISSING_MODELS') {
  // Show AI suggestions to user
  data.missing_models.forEach(model => {
    console.log(`Missing: ${model.filename}`);
    model.ai_suggestions.forEach(suggestion => {
      console.log(`  Suggestion: ${suggestion.filename} (${suggestion.relevance_score})`);
    });
  });
}
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing required parameters)
- `500`: Server error

Error responses include detailed messages:
```json
{
  "success": false,
  "error": "Detailed error message"
}
```

## Performance Considerations

1. **Caching**: Results are cached for 15 minutes to improve performance
2. **Parallel Search**: Multiple sources are searched concurrently
3. **Rate Limiting**: Be mindful of API rate limits for external services
4. **Timeout**: Searches timeout after 30 seconds

## Security

- API keys should be kept secure and not exposed in client code
- Download URLs are validated before being returned
- Checksums are provided when available for verification