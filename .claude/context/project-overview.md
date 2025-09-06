---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# Project Overview

## ComfyUI-Launcher Feature Overview

### Core Features

#### 1. Project Management System
- **Project Dashboard**: Visual grid view of all projects
- **Project Cards**: Display project info, status, and actions
- **Quick Actions**: Launch, delete, open folder
- **Project States**: Running, stopped, installing
- **Port Assignment**: Automatic port allocation from pool

#### 2. Workflow Import System
- **Import Methods**:
  - URL import (ComfyWorkflows.com, CivitAI, direct links)
  - File upload (JSON, ZIP)
  - Drag and drop interface
- **Workflow Parsing**: 
  - Extracts model requirements
  - Identifies custom nodes
  - Detects Python dependencies
- **Validation**: Pre-import compatibility checking
- **Asset Handling**: Images, examples, documentation

#### 3. Model Management
- **Model Discovery**:
  - Automatic detection from workflow JSON
  - Multiple model types (checkpoints, LoRA, VAE, embeddings)
  - Smart filename matching
- **Download Sources**:
  - CivitAI API integration
  - Hugging Face support
  - Direct URL downloads
  - Fallback mechanisms
- **Storage Features**:
  - Centralized model storage
  - Shared across projects
  - Duplicate prevention
  - Storage usage tracking

#### 4. Installation System
- **Environment Setup**:
  - Creates Python virtual environment
  - Installs ComfyUI from git
  - Configures for CPU/GPU
- **Dependency Management**:
  - Custom node installation via git
  - Python package management
  - Version conflict resolution
- **Progress Tracking**:
  - Real-time progress bars
  - Stage-based updates
  - Detailed logging

#### 5. Real-Time Monitoring
- **WebSocket Integration**:
  - Live progress updates
  - Log streaming
  - Error notifications
- **UI Components**:
  - Progress indicators
  - Log viewer with filtering
  - Status badges
  - Storage meter

#### 6. Settings Management
- **Configuration Options**:
  - ComfyUI repository URL
  - Model download settings
  - Port range configuration
  - API keys (CivitAI, HuggingFace)
- **Persistence**: Settings saved to disk
- **Environment Variables**: Override support

### Advanced Features

#### 1. Error Handling
- **Graceful Degradation**: Continues when optional features fail
- **Retry Logic**: Automatic retry for network failures
- **User Guidance**: Actionable error messages
- **Recovery Options**: Manual intervention paths

#### 2. Cloud Integration
- **RunPod Support**: Special cloud environment handling
- **Docker Compatibility**: Container-ready architecture
- **Remote Access**: Network-accessible setup

#### 3. Developer Tools
- **API Documentation**: Comprehensive REST API
- **Debug Utilities**: Logging and inspection tools
- **Test Suite**: Extensive automated tests
- **Extension Points**: Pluggable architecture

### User Interface

#### 1. Main Dashboard
- **Project Grid**: Responsive card layout
- **Search/Filter**: Find projects quickly
- **Batch Operations**: Multi-select actions
- **Statistics**: Overall system status

#### 2. Import Workflow Page
- **Multi-Step Process**: Guided workflow
- **Preview**: See workflow details before import
- **Options**: Customize installation
- **Validation**: Check before proceeding

#### 3. Settings Page
- **Tabbed Interface**: Organized settings
- **Live Preview**: See changes immediately
- **Reset Options**: Restore defaults
- **Advanced Mode**: Power user features

#### 4. Project Details
- **Launch Interface**: ComfyUI in iframe
- **Control Panel**: Start/stop/restart
- **Logs View**: Installation and runtime logs
- **Resource Usage**: Memory/CPU monitoring

### Integration Points

#### 1. ComfyUI Integration
- **Version Management**: Supports multiple versions
- **Custom Node Ecosystem**: Full compatibility
- **Workflow Format**: Native JSON support
- **API Access**: Direct ComfyUI API usage

#### 2. External Services
- **Model Repositories**: CivitAI, HuggingFace
- **Git Repositories**: Custom nodes
- **Package Registries**: PyPI for Python packages
- **Cloud Providers**: RunPod, potential others

#### 3. System Integration
- **File System**: Organized directory structure
- **Process Management**: Subprocess control
- **Network**: Port management and proxy
- **OS Features**: Cross-platform support

### Current State

#### Implemented Features
- ✅ Full project lifecycle management
- ✅ Workflow import from multiple sources
- ✅ Automatic model discovery and download
- ✅ Real-time progress tracking
- ✅ WebSocket communication
- ✅ Error handling and recovery
- ✅ Settings persistence
- ✅ Storage management

#### In Development
- 🚧 Enhanced model source support
- 🚧 Workflow template system
- 🚧 Performance optimizations
- 🚧 Extended cloud support

#### Future Roadmap
- 📋 Model update notifications
- 📋 Workflow versioning
- 📋 Team collaboration features
- 📋 Advanced caching strategies