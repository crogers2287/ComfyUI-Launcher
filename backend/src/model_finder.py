"""
Enhanced Model Finder for ComfyUI-Launcher
Searches multiple sources to find missing models using AI-powered search
"""

import os
import re
import json
import hashlib
import urllib.parse
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Import recovery components
try:
    from .recovery import recoverable
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelSource(Enum):
    """Supported model sources"""
    CIVITAI = "civitai"
    HUGGINGFACE = "huggingface"
    GITHUB = "github"
    DIRECT_URL = "direct_url"
    UNKNOWN = "unknown"


@dataclass
class ModelResult:
    """Model search result"""
    filename: str
    source: ModelSource
    url: str
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    sha256_checksum: Optional[str] = None
    description: Optional[str] = None
    model_type: Optional[str] = None
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PerplexitySearcher:
    """Search for models using Perplexity AI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def search(self, query: str, focus_sources: List[str] = None) -> Dict[str, Any]:
        """Search using Perplexity API"""
        try:
            # Enhance query with ComfyUI context
            enhanced_query = f"ComfyUI model {query} download URL safetensors checkpoint"
            
            # Add source-specific hints
            if focus_sources:
                source_hints = " OR ".join([f"site:{source}" for source in focus_sources])
                enhanced_query += f" ({source_hints})"
            
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that finds download URLs for ComfyUI models. Always provide direct download links when available."
                    },
                    {
                        "role": "user",
                        "content": f"Find the download URL for this ComfyUI model: {query}. Include file size, checksum, and direct download link if available. Focus on CivitAI, Hugging Face, and GitHub releases."
                    }
                ],
                "temperature": 0.1,
                "top_p": 0.9,
                "return_citations": True
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Perplexity search error: {str(e)}")
            return None


class ModelFinder:
    """Enhanced model finder that searches multiple sources"""
    
    def __init__(self, perplexity_api_key: str):
        self.perplexity = PerplexitySearcher(perplexity_api_key)
        self.civitai_base = "https://civitai.com/api/v1"
        self.hf_base = "https://huggingface.co"
        
    # Apply recovery decorator to find_model method if available
    if RECOVERY_AVAILABLE:
        find_model = recoverable(
            max_retries=3,
            initial_delay=3.0,
            backoff_factor=2.0,
            max_delay=120.0,
            timeout=120.0,  # 2 minutes for model search
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=600.0  # 10 minutes
        )(find_model)
    
    def find_model(self, filename: str, model_type: Optional[str] = None) -> List[ModelResult]:
        """
        Find a model by filename across multiple sources
        
        Args:
            filename: The model filename to search for
            model_type: Optional model type hint (checkpoint, lora, vae, etc.)
            
        Returns:
            List of ModelResult objects sorted by relevance
        """
        results = []
        
        # Clean filename for searching
        clean_name = self._clean_filename(filename)
        
        # Search strategies
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            # 1. Direct filename search
            futures.append(executor.submit(self._search_by_exact_filename, filename))
            
            # 2. Perplexity AI search
            futures.append(executor.submit(self._search_with_perplexity, filename, model_type))
            
            # 3. CivitAI search
            futures.append(executor.submit(self._search_civitai, clean_name))
            
            # 4. Hugging Face search
            futures.append(executor.submit(self._search_huggingface, clean_name))
            
            # Collect results
            for future in as_completed(futures):
                try:
                    search_results = future.result()
                    if search_results:
                        results.extend(search_results)
                except Exception as e:
                    logger.error(f"Search error: {str(e)}")
        
        # Deduplicate and rank results
        unique_results = self._deduplicate_results(results)
        ranked_results = self._rank_results(unique_results, filename)
        
        return ranked_results
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename for searching"""
        # Remove extension
        name = os.path.splitext(filename)[0]
        
        # Replace common separators with spaces
        name = re.sub(r'[-_.]', ' ', name)
        
        # Remove version numbers but keep them for later matching
        name = re.sub(r'\b[vV]?\d+(\.\d+)*\b', '', name)
        
        # Remove common suffixes
        suffixes = ['fp16', 'fp32', 'pruned', 'ema', 'vae', 'inpainting']
        for suffix in suffixes:
            name = re.sub(rf'\b{suffix}\b', '', name, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        name = ' '.join(name.split())
        
        return name
    
    def _search_with_perplexity(self, filename: str, model_type: Optional[str]) -> List[ModelResult]:
        """Search using Perplexity AI"""
        results = []
        
        # Focus on model repository sites
        focus_sources = ["civitai.com", "huggingface.co", "github.com"]
        
        response = self.perplexity.search(filename, focus_sources)
        if not response:
            return results
        
        try:
            # Parse Perplexity response
            content = response['choices'][0]['message']['content']
            citations = response.get('citations', [])
            
            # Extract URLs from response and citations
            urls = set()
            
            # Extract from content
            content_urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
            urls.update(content_urls)
            
            # Extract from citations
            for citation in citations:
                if 'url' in citation:
                    urls.add(citation['url'])
            
            # Process each unique URL
            for url in urls:
                # Clean URL
                url = url.rstrip('.,;:)')
                
                # Determine source
                source = self._determine_source(url)
                
                # Create result
                result = ModelResult(
                    filename=filename,
                    source=source,
                    url=url,
                    download_url=self._extract_download_url(url, source),
                    relevance_score=0.9,  # High score for AI-found results
                    metadata={'ai_suggested': True}
                )
                
                # Try to extract additional info from content
                self._enrich_result_from_content(result, content)
                
                # Update download URL if we found a direct link in content
                if not result.download_url:
                    # Look for direct download links in content
                    download_patterns = [
                        rf'download[^"]*"([^"]*{re.escape(filename)}[^"]*)"',
                        rf'href="([^"]*{re.escape(filename)}[^"]*)"',
                        rf'(https://[^\s]+/{re.escape(filename)})'
                    ]
                    
                    for pattern in download_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            result.download_url = matches[0]
                            break
                
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error parsing Perplexity response: {str(e)}")
        
        return results
    
    def _search_civitai(self, query: str) -> List[ModelResult]:
        """Search CivitAI for models"""
        results = []
        
        try:
            # Search CivitAI API
            params = {
                'query': query,
                'limit': 10,
                'types': 'Checkpoint,LORA,TextualInversion,VAE'
            }
            
            response = requests.get(
                f"{self.civitai_base}/models",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for model in data.get('items', []):
                    # Get model versions
                    for version in model.get('modelVersions', []):
                        for file in version.get('files', []):
                            if file['name'].endswith(('.safetensors', '.ckpt', '.pt')):
                                result = ModelResult(
                                    filename=file['name'],
                                    source=ModelSource.CIVITAI,
                                    url=f"https://civitai.com/models/{model['id']}",
                                    download_url=file.get('downloadUrl'),
                                    file_size=file.get('sizeKB', 0) * 1024 if file.get('sizeKB') else None,
                                    sha256_checksum=file.get('hashes', {}).get('SHA256'),
                                    description=model.get('description'),
                                    model_type=model.get('type'),
                                    relevance_score=self._calculate_relevance(query, file['name']),
                                    metadata={
                                        'model_id': model['id'],
                                        'version_id': version['id'],
                                        'file_id': file.get('id')
                                    }
                                )
                                results.append(result)
                                
        except Exception as e:
            logger.error(f"CivitAI search error: {str(e)}")
        
        return results
    
    def _search_huggingface(self, query: str) -> List[ModelResult]:
        """Search Hugging Face for models"""
        results = []
        
        try:
            # Search HF models
            params = {
                'search': query,
                'filter': 'text-to-image,diffusers',
                'limit': 10
            }
            
            response = requests.get(
                f"{self.hf_base}/api/models",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for model in data:
                    model_id = model['modelId']
                    
                    # Get model files
                    files_response = requests.get(
                        f"{self.hf_base}/api/models/{model_id}/tree/main",
                        timeout=10
                    )
                    
                    if files_response.status_code == 200:
                        files = files_response.json()
                        
                        for file in files:
                            if file['path'].endswith(('.safetensors', '.ckpt', '.pt')):
                                result = ModelResult(
                                    filename=os.path.basename(file['path']),
                                    source=ModelSource.HUGGINGFACE,
                                    url=f"{self.hf_base}/{model_id}",
                                    download_url=f"{self.hf_base}/{model_id}/resolve/main/{file['path']}",
                                    file_size=file.get('size'),
                                    model_type=self._guess_model_type(file['path']),
                                    relevance_score=self._calculate_relevance(query, file['path']),
                                    metadata={
                                        'model_id': model_id,
                                        'path': file['path']
                                    }
                                )
                                results.append(result)
                                
        except Exception as e:
            logger.error(f"Hugging Face search error: {str(e)}")
        
        return results
    
    def _search_by_exact_filename(self, filename: str) -> List[ModelResult]:
        """Try to find model by exact filename match"""
        results = []
        
        # Try constructing common URLs
        base_urls = [
            f"https://huggingface.co/stabilityai/stable-diffusion-2-1/resolve/main/{filename}",
            f"https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/{filename}",
            f"https://huggingface.co/CompVis/stable-diffusion-v1-4/resolve/main/{filename}",
        ]
        
        for url in base_urls:
            try:
                # Check if URL exists
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    result = ModelResult(
                        filename=filename,
                        source=self._determine_source(url),
                        url=url,
                        download_url=url,
                        relevance_score=1.0  # Perfect match
                    )
                    results.append(result)
            except:
                pass
        
        return results
    
    def _determine_source(self, url: str) -> ModelSource:
        """Determine the source from URL"""
        if 'civitai.com' in url:
            return ModelSource.CIVITAI
        elif 'huggingface.co' in url:
            return ModelSource.HUGGINGFACE
        elif 'github.com' in url:
            return ModelSource.GITHUB
        else:
            return ModelSource.DIRECT_URL
    
    def _extract_download_url(self, url: str, source: ModelSource) -> Optional[str]:
        """Extract direct download URL from page URL"""
        if source == ModelSource.CIVITAI:
            # CivitAI model page to API download URL
            match = re.search(r'/models/(\d+)', url)
            if match:
                model_id = match.group(1)
                try:
                    # Get model details from CivitAI API
                    response = requests.get(f"{self.civitai_base}/models/{model_id}", timeout=10)
                    if response.status_code == 200:
                        model_data = response.json()
                        # Get the latest version's files
                        if model_data.get('modelVersions'):
                            latest_version = model_data['modelVersions'][0]
                            for file in latest_version.get('files', []):
                                if file['name'].endswith(('.safetensors', '.ckpt', '.pt')):
                                    return file.get('downloadUrl')
                except Exception as e:
                    logger.error(f"Error fetching CivitAI download URL: {str(e)}")
                return None
        elif source == ModelSource.HUGGINGFACE:
            # Convert HF model page to download URL
            if '/blob/' in url:
                return url.replace('/blob/', '/resolve/')
        
        return url if url.endswith(('.safetensors', '.ckpt', '.pt')) else None
    
    def _enrich_result_from_content(self, result: ModelResult, content: str):
        """Extract additional info from AI response content"""
        # Try to extract file size
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|KB)', content, re.IGNORECASE)
        if size_match:
            size, unit = size_match.groups()
            multipliers = {'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
            result.file_size = int(float(size) * multipliers.get(unit.upper(), 1))
        
        # Try to extract checksum
        sha_match = re.search(r'SHA256:?\s*([a-fA-F0-9]{64})', content)
        if sha_match:
            result.sha256_checksum = sha_match.group(1)
    
    def _calculate_relevance(self, query: str, filename: str) -> float:
        """Calculate relevance score between query and filename"""
        query_lower = query.lower()
        filename_lower = filename.lower()
        
        # Exact match
        if query_lower == filename_lower:
            return 1.0
        
        # Filename contains query
        if query_lower in filename_lower:
            return 0.8
        
        # All query words in filename
        query_words = set(query_lower.split())
        filename_words = set(filename_lower.replace('-', ' ').replace('_', ' ').split())
        
        if query_words.issubset(filename_words):
            return 0.7
        
        # Partial word matches
        matching_words = query_words.intersection(filename_words)
        if matching_words:
            return 0.5 * (len(matching_words) / len(query_words))
        
        return 0.1
    
    def _deduplicate_results(self, results: List[ModelResult]) -> List[ModelResult]:
        """Remove duplicate results based on download URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url_key = result.download_url or result.url
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_results.append(result)
        
        return unique_results
    
    def _rank_results(self, results: List[ModelResult], original_filename: str) -> List[ModelResult]:
        """Rank results by relevance and source reliability"""
        # Boost score for exact filename matches
        for result in results:
            if result.filename.lower() == original_filename.lower():
                result.relevance_score = min(1.0, result.relevance_score + 0.3)
        
        # Sort by relevance score (descending)
        return sorted(results, key=lambda r: r.relevance_score, reverse=True)
    
    def _guess_model_type(self, filepath: str) -> Optional[str]:
        """Guess model type from filepath"""
        filepath_lower = filepath.lower()
        
        if 'vae' in filepath_lower:
            return 'vae'
        elif 'lora' in filepath_lower or 'lycoris' in filepath_lower:
            return 'lora'
        elif 'embedding' in filepath_lower or 'textual' in filepath_lower:
            return 'embedding'
        elif 'controlnet' in filepath_lower:
            return 'controlnet'
        elif 'checkpoint' in filepath_lower or 'ckpt' in filepath_lower:
            return 'checkpoint'
        
        return None


# Example usage and testing
if __name__ == "__main__":
    # Test with the specific model mentioned
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    finder = ModelFinder(api_key)
    
    test_filename = "Wan2.1_T2V_14B_FusionX_LoRA.safetensors"
    print(f"Searching for: {test_filename}")
    
    results = finder.find_model(test_filename)
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results[:5]):  # Show top 5
        print(f"\n{i+1}. {result.filename}")
        print(f"   Source: {result.source.value}")
        print(f"   URL: {result.url}")
        print(f"   Download: {result.download_url}")
        print(f"   Relevance: {result.relevance_score:.2f}")
        if result.file_size:
            print(f"   Size: {result.file_size / (1024*1024):.1f} MB")