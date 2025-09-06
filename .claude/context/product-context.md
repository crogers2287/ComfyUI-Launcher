---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# Product Context

## Product Overview

ComfyUI-Launcher is a **bulletproof dependency management tool** for ComfyUI workflows, solving the complex problem of managing models, dependencies, and isolated environments for AI image generation workflows.

## Target Users

### Primary Users
1. **AI Artists and Creators**
   - Need reliable workflow execution
   - Want automatic model management
   - Require isolated project environments
   - Share workflows with specific dependencies

2. **ComfyUI Power Users**
   - Manage multiple projects simultaneously
   - Test different model combinations
   - Collaborate on complex workflows
   - Need reproducible environments

3. **Workflow Developers**
   - Create and distribute workflows
   - Ensure dependency compatibility
   - Package workflows with requirements
   - Provide one-click setup for users

### Secondary Users
1. **Cloud Service Providers** (RunPod integration)
2. **Educational Institutions** teaching AI art
3. **Studios** managing team workflows

## Core Functionality

### 1. Project Management
- **Isolated Environments**: Each project gets its own Python virtual environment
- **Port Management**: Automatic port allocation (4001-4100)
- **Project Dashboard**: Visual management of all projects
- **One-Click Launch**: Start ComfyUI instances instantly

### 2. Workflow Import System
- **Multiple Import Methods**:
  - Direct URL import
  - File upload (JSON/ZIP)
  - ComfyWorkflows.com integration
  - Drag-and-drop support
- **Automatic Parsing**: Extracts requirements from workflow JSON
- **Validation**: Pre-import checking for compatibility

### 3. Model Management
- **Automatic Discovery**: Finds required models in workflows
- **Multi-Source Downloads**:
  - CivitAI
  - Hugging Face
  - Direct URLs
- **Shared Storage**: Models cached and shared between projects
- **Progress Tracking**: Real-time download progress
- **Storage Management**: Monitor and clean up model storage

### 4. Dependency Resolution
- **Custom Nodes**: Automatic installation of required nodes
- **Python Packages**: pip requirements handling
- **Version Management**: Ensures compatibility
- **Fallback Handling**: Graceful degradation when unavailable

### 5. Real-Time Monitoring
- **Live Logs**: Stream installation and execution logs
- **Progress Updates**: WebSocket-based progress tracking
- **Error Reporting**: Detailed error messages with solutions
- **System Status**: CPU/Memory/Disk monitoring

## Use Cases

### Primary Use Cases

1. **Workflow Sharing**
   - Creator publishes workflow with complex dependencies
   - User imports with one click
   - All models and nodes automatically installed
   - Workflow runs identically to creator's setup

2. **Project Isolation**
   - Run SD1.5 project alongside SDXL project
   - Different ComfyUI versions per project
   - No dependency conflicts
   - Easy switching between projects

3. **Team Collaboration**
   - Share project configurations
   - Reproducible environments
   - Centralized model storage
   - Consistent setups across team

### Advanced Use Cases

1. **Workflow Development**
   - Test workflows in clean environments
   - Validate dependency specifications
   - Package for distribution
   - Debug compatibility issues

2. **Cloud Deployment**
   - RunPod integration
   - Dockerized deployments
   - Remote access capabilities
   - Scalable infrastructure

## Key Differentiators

### vs Manual ComfyUI Setup
- **Automatic vs Manual**: No manual model hunting
- **Isolated vs Global**: No Python conflicts
- **Managed vs Chaotic**: Organized project structure
- **Tracked vs Unknown**: Know what's installed where

### vs Other Launchers
- **Bulletproof**: Emphasis on reliability
- **Project-Based**: Not just a single installation
- **Dependency-Aware**: Understands workflow requirements
- **Real-Time Feedback**: Live progress and logs

## Success Metrics

### User Success
- Time from workflow import to first run: <5 minutes
- Model download success rate: >95%
- Project launch success rate: >99%
- Zero dependency conflicts between projects

### Technical Success
- Automatic model discovery accuracy
- Download retry resilience
- Error recovery capabilities
- Resource usage optimization

## Future Vision

### Planned Features
- Model update notifications
- Workflow versioning
- Team workspace support
- Cloud model caching
- Workflow marketplace integration

### Expansion Opportunities
- Support for other AI frameworks
- Workflow optimization tools
- Performance profiling
- Collaborative editing