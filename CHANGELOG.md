# Changelog

All notable changes to ComfyUI Launcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-08-30

### Added
- Initial release of ComfyUI Launcher
- Bulletproof dependency installation with parallel downloads and retry logic
- AI-powered model finding using Perplexity API
- Support for importing workflows from ZIP files
- URL import feature for direct workflow loading
- Modern dark mode UI with Tailwind CSS
- Real-time progress tracking via WebSocket
- Backend API for model management and workflow processing
- Frontend React application with TypeScript
- Comprehensive test suite with 70%+ coverage
- GitHub Actions CI/CD pipeline
- Docker support for containerized deployment
- Redis/Celery for background task processing

### Fixed
- React hooks errors in UI components
- URL validation for HuggingFace resolve URLs
- File path handling for cross-platform compatibility
- Import process for complex workflows

### Security
- Secure model download validation with checksums
- Input sanitization for file uploads
- API rate limiting for external requests

### Infrastructure
- Restructured project for better maintainability
- Added comprehensive documentation
- Set up automated testing and linting
- Configured pre-commit hooks

[0.1.0]: https://github.com/comfyui-launcher/comfyui-launcher/releases/tag/v0.1.0