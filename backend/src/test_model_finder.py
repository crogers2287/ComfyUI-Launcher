#!/usr/bin/env python3
"""Test script for the enhanced model finder"""

import requests
import json
import sys
from backend.src.model_finder import ModelFinder

def test_direct_finder():
    """Test the ModelFinder class directly"""
    print("=== Testing ModelFinder directly ===")
    
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    finder = ModelFinder(api_key)
    
    # Test cases
    test_models = [
        "Wan2.1_T2V_14B_FusionX_LoRA.safetensors",
        "sd_xl_base_1.0.safetensors",
        "realisticVisionV51_v51VAE.safetensors",
        "control_v11p_sd15_openpose.pth"
    ]
    
    for model_name in test_models:
        print(f"\nSearching for: {model_name}")
        results = finder.find_model(model_name)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results[:3]):  # Show top 3
                print(f"\n  {i+1}. {result.filename}")
                print(f"     Source: {result.source.value}")
                print(f"     URL: {result.url}")
                print(f"     Download: {result.download_url}")
                print(f"     Relevance: {result.relevance_score:.2f}")
                if result.file_size:
                    print(f"     Size: {result.file_size / (1024*1024):.1f} MB")
                if result.sha256_checksum:
                    print(f"     SHA256: {result.sha256_checksum[:16]}...")
        else:
            print("  No results found")

def test_api_endpoint():
    """Test the API endpoint"""
    print("\n\n=== Testing API endpoint ===")
    
    base_url = "http://localhost:5000"
    endpoint = f"{base_url}/api/find_model"
    
    test_payload = {
        "filename": "Wan2.1_T2V_14B_FusionX_LoRA.safetensors",
        "model_type": "lora"
    }
    
    try:
        response = requests.post(endpoint, json=test_payload)
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Found {len(data['results'])} results")
            
            for i, result in enumerate(data['results'][:3]):
                print(f"\n  {i+1}. {result['filename']}")
                print(f"     Source: {result['source']}")
                print(f"     URL: {result['url']}")
                print(f"     Download: {result['download_url']}")
                print(f"     Relevance: {result['relevance_score']:.2f}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Make sure the server is running on port 5000")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        test_api_endpoint()
    else:
        test_direct_finder()
        print("\n\nTo test the API endpoint, run: python test_model_finder.py api")