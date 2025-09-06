"""
Celery app wrapper for ComfyUI Launcher
"""
# Import the celery app from server
from backend.src.server import celery_app

# Export it for use with celery command
__all__ = ['celery_app']