"""
Automatic model downloader for ComfyUI workflows
Detects and downloads ALL missing models automatically
"""
import os
import json
import requests
from typing import Dict, List, Optional
from model_finder import ModelFinder
from utils import DownloadManager

# Import recovery components
try:
    from .recovery import recoverable
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False

# Known model mappings for common checkpoints
KNOWN_MODELS = {
    "v1-5-pruned-emaonly-fp16.safetensors": {
        "url": "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly-fp16.safetensors",
        "type": "checkpoints",
        "size": "2.13 GB"
    },
    "v1-5-pruned-emaonly.safetensors": {
        "url": "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors", 
        "type": "checkpoints",
        "size": "4.27 GB"
    },
    "sd_xl_base_1.0.safetensors": {
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "type": "checkpoints",
        "size": "6.94 GB"
    },
    # WAN 2.2 models
    "wan2.2_ti2v_5B_fp16.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors",
        "type": "diffusion_models",
        "size": "9.8 GB"
    },
    "wan2.2_vae.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors",
        "type": "vae",
        "size": "325 MB"
    },
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "type": "text_encoders",
        "size": "9.5 GB"
    },
    # Also add common aliases
    "wan_2.1_vae.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors",
        "type": "vae",
        "size": "325 MB"
    },
    "wan_2.2_i2v_rapid.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors",
        "type": "diffusion_models",
        "size": "9.8 GB"
    },
    "umt5-xxl-enc-fp8_e4m3fn.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "type": "text_encoders",
        "size": "9.5 GB"
    },
    # GGUF versions
    "wan_2.2_i2v_rapid-Q4_K_M.gguf": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.2_GGUF_ComfyUI/resolve/main/diffusion_models/wan_2.2_i2v_rapid-Q4_K_M.gguf",
        "type": "diffusion_models",
        "size": "5.3 GB"
    },
    "umt5-xxl-encoder-Q8_0.gguf": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_GGUF_ComfyUI/resolve/main/text_encoders/umt5-xxl-encoder-Q8_0.gguf",
        "type": "text_encoders", 
        "size": "9.7 GB"
    }
}

def detect_missing_models(workflow_json: dict, project_path: str) -> List[Dict]:
    """Detect all missing models in a workflow"""
    missing_models = []
    models_with_urls = {}  # Track models that have URLs
    
    # Handle both old and new workflow formats
    nodes = workflow_json.get("nodes", [])
    
    # If nodes is a list (new format), iterate directly
    if isinstance(nodes, list):
        for node_data in nodes:
            if not isinstance(node_data, dict):
                continue
                
            node_type = node_data.get("type", "")
            node_id = node_data.get("id", "")
            widgets_values = node_data.get("widgets_values", [])
            node_properties = node_data.get("properties", {})
            
            # Track if this node has models in properties
            has_embedded_models = False
            
            # Check for models in node properties (new format with embedded URLs)
            if "models" in node_properties and isinstance(node_properties["models"], list):
                for model_info in node_properties["models"]:
                    if isinstance(model_info, dict) and "name" in model_info:
                        model_name = model_info["name"]
                        model_dir = model_info.get("directory", "")
                        
                        # Map directory to model type
                        dir_to_type_map = {
                            "diffusion_models": "diffusion_models",
                            "checkpoints": "checkpoints",
                            "vae": "vae",
                            "text_encoders": "text_encoders",
                            "clip": "clip",
                            "loras": "loras"
                        }
                        
                        model_type = dir_to_type_map.get(model_dir, model_dir)
                        model_path = os.path.join(project_path, "comfyui/models", model_type, model_name)
                        
                        if not os.path.exists(model_path):
                            models_with_urls[model_name] = {
                                "filename": model_name,
                                "type": model_type,
                                "node_type": node_type,
                                "node_id": node_id,
                                "download_url": model_info.get("url"),  # Include URL if provided
                                "dest_relative_path": os.path.join("comfyui/models", model_type, model_name)
                            }
                            has_embedded_models = True
            
            # Check widgets_values for model references (both formats)
            # Skip if we already found this model in properties.models
            # Also skip MarkdownNote nodes which contain documentation URLs
            if widgets_values and not has_embedded_models and node_type != "MarkdownNote":
                # UNETLoader, CheckpointLoader, UnetLoaderGGUF
                if "UNET" in node_type or "Unet" in node_type or "Checkpoint" in node_type:
                    if len(widgets_values) > 0 and isinstance(widgets_values[0], str):
                        model_name = widgets_values[0]
                        # Skip if this looks like a URL
                        if not model_name.startswith(("http://", "https://", "ftp://")):
                            model_type = "diffusion_models" if ("UNET" in node_type or "Unet" in node_type) else "checkpoints"
                            model_path = os.path.join(project_path, "comfyui/models", model_type, model_name)
                            if not os.path.exists(model_path):
                                missing_models.append({
                                    "filename": model_name,
                                    "type": model_type,
                                    "node_type": node_type,
                                    "node_id": node_id,
                                    "dest_relative_path": os.path.join("comfyui/models", model_type, model_name)
                                })
                
                # VAELoader
                elif "VAE" in node_type:
                    if len(widgets_values) > 0 and isinstance(widgets_values[0], str):
                        model_name = widgets_values[0]
                        # Skip if this looks like a URL
                        if not model_name.startswith(("http://", "https://", "ftp://")):
                            model_path = os.path.join(project_path, "comfyui/models/vae", model_name)
                            if not os.path.exists(model_path):
                                missing_models.append({
                                    "filename": model_name,
                                    "type": "vae",
                                    "node_type": node_type,
                                    "node_id": node_id,
                                    "dest_relative_path": os.path.join("comfyui/models/vae", model_name)
                                })
                
                # CLIPLoader, CLIPLoaderGGUF
                elif "CLIPLoader" in node_type:
                    if len(widgets_values) > 0 and isinstance(widgets_values[0], str):
                        model_name = widgets_values[0]
                        # Skip if this looks like a URL
                        if not model_name.startswith(("http://", "https://", "ftp://")):
                            model_type = "text_encoders" if "text_encoder" in model_name.lower() or "umt5" in model_name.lower() or "encoder" in model_name.lower() else "clip"
                            model_path = os.path.join(project_path, "comfyui/models", model_type, model_name)
                            if not os.path.exists(model_path):
                                missing_models.append({
                                    "filename": model_name,
                                    "type": model_type,
                                    "node_type": node_type,
                                    "node_id": node_id,
                                    "dest_relative_path": os.path.join("comfyui/models", model_type, model_name)
                                })
                
                # LoRALoader
                elif "LoRA" in node_type or "Lora" in node_type:
                    if len(widgets_values) > 0 and isinstance(widgets_values[0], str):
                        model_name = widgets_values[0]
                        # Skip if this looks like a URL
                        if not model_name.startswith(("http://", "https://", "ftp://")):
                            model_path = os.path.join(project_path, "comfyui/models/loras", model_name)
                            if not os.path.exists(model_path):
                                missing_models.append({
                                    "filename": model_name,
                                    "type": "loras",
                                    "node_type": node_type,
                                    "node_id": node_id,
                                    "dest_relative_path": os.path.join("comfyui/models/loras", model_name)
                                })
    
    # Handle old format where nodes is a dict
    elif isinstance(nodes, dict):
        for node_id, node_data in nodes.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})
            
            # Checkpoint loaders
            if "Checkpoint" in class_type and "ckpt_name" in inputs:
                model_name = inputs["ckpt_name"]
                model_path = os.path.join(project_path, "comfyui/models/checkpoints", model_name)
                if not os.path.exists(model_path):
                    missing_models.append({
                        "filename": model_name,
                        "type": "checkpoints",
                        "node_type": class_type,
                        "node_id": node_id,
                        "dest_relative_path": os.path.join("comfyui/models/checkpoints", model_name)
                    })
            
            # VAE loaders
            if "VAE" in class_type and "vae_name" in inputs:
                model_name = inputs["vae_name"]
                model_path = os.path.join(project_path, "comfyui/models/vae", model_name)
                if not os.path.exists(model_path):
                    missing_models.append({
                        "filename": model_name,
                        "type": "vae",
                        "node_type": class_type,
                        "node_id": node_id,
                        "dest_relative_path": os.path.join("comfyui/models/vae", model_name)
                    })
            
            # LoRA loaders
            if "LoRA" in class_type and "lora_name" in inputs:
                model_name = inputs["lora_name"]
                model_path = os.path.join(project_path, "comfyui/models/loras", model_name)
                if not os.path.exists(model_path):
                    missing_models.append({
                        "filename": model_name,
                        "type": "loras",
                        "node_type": class_type,
                        "node_id": node_id,
                        "dest_relative_path": os.path.join("comfyui/models/loras", model_name)
                    })
                    
            # CLIP/Text encoder loaders
            if "CLIP" in class_type and "clip_name" in inputs:
                model_name = inputs["clip_name"]
                model_path = os.path.join(project_path, "comfyui/models/clip", model_name)
                if not os.path.exists(model_path):
                    missing_models.append({
                        "filename": model_name,
                        "type": "clip",
                        "node_type": class_type,
                        "node_id": node_id,
                        "dest_relative_path": os.path.join("comfyui/models/clip", model_name)
                    })
    
    # Add models with URLs first
    final_models = list(models_with_urls.values())
    
    # Then add any models from widgets_values that weren't in properties
    seen = set((m["filename"], m["type"]) for m in final_models)
    for model in missing_models:
        key = (model["filename"], model["type"])
        if key not in seen:
            final_models.append(model)
            seen.add(key)
    
    return final_models

# Apply recovery decorator to auto_download_models if available
if RECOVERY_AVAILABLE:
    auto_download_models = recoverable(
        max_retries=3,
        initial_delay=5.0,
        backoff_factor=2.0,
        max_delay=300.0,
        timeout=1800.0,  # 30 minutes for auto download
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=600.0  # 10 minutes
    )(auto_download_models)
else:
    # If recovery not available, use original function
    pass

def auto_download_models(project_path: str, workflow_json: dict, log_callback=None) -> Dict:
    """Automatically find and download all missing models for a workflow"""
    
    missing_models = detect_missing_models(workflow_json, project_path)
    
    if not missing_models:
        if log_callback:
            log_callback('info', 'No missing models detected')
        return {"success": True, "downloaded": 0, "failed": 0}
    
    if log_callback:
        log_callback('info', f'Found {len(missing_models)} missing models')
    
    # Initialize download manager
    download_manager = DownloadManager(max_workers=2)
    
    # Try to find and download each model
    downloaded = 0
    failed = []
    
    for model in missing_models:
        filename = model["filename"]
        model_type = model["type"]
        url = None
        
        # First check if URL was provided in the workflow
        if "download_url" in model and model["download_url"]:
            url = model["download_url"]
            if log_callback:
                log_callback('info', f'Using workflow-provided URL for {filename}')
        # Then check if we have a known URL
        elif filename in KNOWN_MODELS:
            model_info = KNOWN_MODELS[filename]
            url = model_info["url"]
            if log_callback:
                log_callback('info', f'Found known URL for {filename}')
        else:
            # Use AI model finder
            if log_callback:
                log_callback('info', f'Searching for {filename} using AI...')
            
            api_key = os.environ.get("PERPLEXITY_API_KEY", "")
            finder = ModelFinder(api_key)
            results = finder.find_model(filename, model_type)
            
            if results and results[0].download_url:
                url = results[0].download_url
                if log_callback:
                    log_callback('info', f'AI found download URL for {filename}')
            else:
                if log_callback:
                    log_callback('warning', f'Could not find download URL for {filename}')
                failed.append(filename)
                continue
        
        # Download the model
        dest_path = os.path.join(project_path, "comfyui/models", model_type, filename)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if log_callback:
            log_callback('info', f'Downloading {filename} to {dest_path}...')
        
        result = download_manager.download_file(url, dest_path)
        
        if result["success"]:
            downloaded += 1
            if log_callback:
                log_callback('info', f'Successfully downloaded {filename}')
        else:
            failed.append(filename)
            if log_callback:
                log_callback('error', f'Failed to download {filename}: {result.get("error")}')
    
    return {
        "success": len(failed) == 0,
        "downloaded": downloaded,
        "failed": len(failed),
        "failed_models": failed,
        "total": len(missing_models)
    }