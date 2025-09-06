---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# Project Brief

## What is ComfyUI-Launcher?

ComfyUI-Launcher is a **dependency management and project isolation tool** for ComfyUI, the node-based AI image generation interface. It automates the complex process of setting up ComfyUI workflows with their required models, custom nodes, and dependencies.

## Why Does It Exist?

### The Problem
ComfyUI workflows often require:
- Specific AI models (often gigabytes in size)
- Custom nodes with their own dependencies
- Specific Python package versions
- Compatible ComfyUI versions

Users face:
- **Dependency Hell**: Conflicting Python packages between workflows
- **Model Hunt**: Manually finding and downloading models
- **Setup Complexity**: Hours spent configuring environments
- **Sharing Difficulties**: Workflows fail on other machines
- **Version Conflicts**: Different workflows need different versions

### The Solution
ComfyUI-Launcher provides:
- **Automatic Setup**: One-click workflow import and setup
- **Isolated Environments**: Each project in its own virtual environment
- **Smart Model Management**: Automatic discovery and download
- **Real-time Feedback**: Progress tracking and error handling
- **Project Organization**: Clean separation between projects

## Core Objectives

### 1. Simplify Workflow Setup
- Import any ComfyUI workflow with one action
- Automatically resolve all dependencies
- Download required models from multiple sources
- Install necessary custom nodes

### 2. Ensure Reliability
- "Bulletproof" dependency management
- Graceful error handling
- Retry mechanisms for downloads
- Clear error messages with solutions

### 3. Enable Isolation
- Separate virtual environment per project
- No conflicts between projects
- Run multiple ComfyUI versions
- Clean uninstall without residue

### 4. Provide Transparency
- Real-time progress updates
- Live installation logs
- Storage usage tracking
- Clear project status

## Success Criteria

### For End Users
- ✅ Can import and run any shared workflow without manual setup
- ✅ Projects always launch successfully
- ✅ No Python dependency conflicts
- ✅ Models download automatically
- ✅ Clear feedback during setup

### For Workflow Creators
- ✅ Workflows run identically on any machine
- ✅ Easy distribution of complex setups
- ✅ Confidence in dependency specification
- ✅ Reduced support burden

### Technical Success
- ✅ 99%+ project launch success rate
- ✅ Automatic retry for failed downloads
- ✅ Efficient model storage (shared between projects)
- ✅ Fast project switching
- ✅ Low resource overhead

## Project Scope

### In Scope
- ComfyUI workflow import and management
- Automatic model downloading
- Custom node installation
- Python dependency management
- Project isolation and organization
- Real-time progress tracking
- Error handling and recovery
- Basic storage management

### Out of Scope
- Workflow editing capabilities
- Model training features
- Cloud compute management (except RunPod integration)
- Workflow marketplace features
- Advanced model optimization

## Target Audience

### Primary
- **ComfyUI users** who run multiple workflows
- **Workflow creators** sharing their work
- **AI artists** needing reliable tools
- **Teams** collaborating on projects

### Secondary
- Cloud service providers
- Educational institutions
- Professional studios
- Workflow marketplaces

## Key Constraints

### Technical
- Must work with existing ComfyUI ecosystem
- Cannot modify ComfyUI core functionality
- Limited by Python virtual environment capabilities
- Dependent on external model hosting services

### User Experience
- Must be simpler than manual setup
- Cannot require technical knowledge
- Must provide clear feedback
- Should handle errors gracefully

## Measurable Goals

1. **Setup Time**: Reduce workflow setup from hours to minutes
2. **Success Rate**: Achieve 95%+ automatic setup success
3. **User Effort**: Require <3 clicks to import and run workflow
4. **Error Recovery**: Successfully retry 90%+ of failed downloads
5. **Storage Efficiency**: Share 80%+ of models between projects