"""Tests for utility functions."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json

from backend.src.utils import (
    check_url_structure,
    slugify,
    get_launcher_json_for_workflow_json,
    extract_workflow_from_zip,
    DownloadManager,
)


class TestCheckUrlStructure:
    """Test URL validation function."""

    def test_valid_huggingface_resolve_url(self):
        """Test valid HuggingFace resolve URLs."""
        url = "https://huggingface.co/Comfy-Org/model/resolve/main/model.safetensors"
        assert check_url_structure(url) is True

    def test_valid_huggingface_blob_url(self):
        """Test valid HuggingFace blob URLs."""
        url = "https://huggingface.co/Comfy-Org/model/blob/main/model.safetensors"
        assert check_url_structure(url) is True

    def test_valid_civitai_url(self):
        """Test valid CivitAI URLs."""
        url = "https://civitai.com/models/12345"
        assert check_url_structure(url) is True

    def test_invalid_url(self):
        """Test invalid URLs."""
        assert check_url_structure("https://example.com/model.safetensors") is False
        assert check_url_structure("not-a-url") is False


class TestSlugify:
    """Test slugify function."""

    def test_basic_slugify(self):
        """Test basic slugification."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test_Model_123") == "test_model_123"

    def test_special_characters(self):
        """Test slugification with special characters."""
        assert slugify("Hello@World#2024") == "helloworld2024"
        assert slugify("  Multiple   Spaces  ") == "multiple-spaces"

    def test_unicode_handling(self):
        """Test unicode handling."""
        assert slugify("Café", allow_unicode=False) == "caf"
        assert slugify("Café", allow_unicode=True) == "café"


class TestDownloadManager:
    """Test DownloadManager class."""

    @patch('backend.src.utils.requests.get')
    def test_download_file_success(self, mock_get):
        """Test successful file download."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {'content-length': '1000'}
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [b'data'] * 10
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DownloadManager(max_workers=1)
            result = dm.download_file(
                "https://example.com/model.bin",
                os.path.join(tmpdir, "model.bin")
            )
            
            assert result['success'] is True
            assert result['size_bytes'] > 0
            assert os.path.exists(result['dest_path'])

    @patch('backend.src.utils.requests.get')
    def test_download_file_retry(self, mock_get):
        """Test download retry on failure."""
        # First attempt fails, second succeeds
        mock_get.side_effect = [
            Exception("Network error"),
            Mock(
                status_code=200,
                headers={'content-length': '100'},
                iter_content=lambda chunk_size: [b'data']
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DownloadManager(max_workers=1)
            result = dm.download_file(
                "https://example.com/model.bin",
                os.path.join(tmpdir, "model.bin"),
                max_retries=2
            )
            
            assert result['success'] is True
            assert mock_get.call_count == 2


class TestExtractWorkflowFromZip:
    """Test ZIP extraction functionality."""

    def test_extract_workflow_json(self):
        """Test extracting workflow.json from ZIP."""
        import zipfile
        
        workflow_data = {"nodes": [{"id": 1, "type": "test"}]}
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            try:
                with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
                    zf.writestr('workflow.json', json.dumps(workflow_data))
                    zf.writestr('assets/image.png', b'fake-image-data')
                
                result = extract_workflow_from_zip(tmp_zip.name)
                
                assert result is not None
                workflow, assets = result
                assert workflow == workflow_data
                assert len(assets) == 1
                assert assets[0]['name'] == 'assets/image.png'
            finally:
                os.unlink(tmp_zip.name)

    def test_extract_no_workflow(self):
        """Test ZIP without workflow.json."""
        import zipfile
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            try:
                with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
                    zf.writestr('readme.txt', 'No workflow here')
                
                result = extract_workflow_from_zip(tmp_zip.name)
                assert result is None
            finally:
                os.unlink(tmp_zip.name)


class TestGetLauncherJsonForWorkflowJson:
    """Test workflow conversion function."""

    @patch('backend.src.utils.get_missing_models')
    def test_workflow_conversion_success(self, mock_get_missing):
        """Test successful workflow conversion."""
        mock_get_missing.return_value = []
        
        workflow = {
            "nodes": [{"id": 1, "type": "KSampler"}],
            "extra": {"ds": {"scale": 1.0}}
        }
        
        result = get_launcher_json_for_workflow_json(workflow)
        
        assert result['success'] is True
        assert 'launcher_json' in result
        assert result['launcher_json']['workflow'] == workflow

    @patch('backend.src.utils.get_missing_models')
    def test_workflow_with_missing_models(self, mock_get_missing):
        """Test workflow with missing models."""
        mock_get_missing.return_value = [
            {
                "filename": "model.safetensors",
                "node_type": "CheckpointLoader",
                "dest_relative_path": "models/checkpoints/model.safetensors"
            }
        ]
        
        workflow = {"nodes": [{"id": 1, "type": "CheckpointLoader"}]}
        
        result = get_launcher_json_for_workflow_json(
            workflow,
            skip_model_validation=False
        )
        
        assert result['success'] is False
        assert result['error'] == 'MISSING_MODELS'
        assert len(result['missing_models']) == 1