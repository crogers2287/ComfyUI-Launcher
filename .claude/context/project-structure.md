---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# Project Structure

## Root Directory Organization

```
ComfyUI-Launcher/
├── backend/                    # Python Flask backend (NEW structure)
│   ├── src/                   # Source code directory
│   │   ├── server.py         # Main Flask application
│   │   ├── tasks.py          # Celery async tasks
│   │   ├── settings.py       # Configuration settings
│   │   ├── utils.py          # Utility functions
│   │   ├── model_finder.py   # Model discovery and download
│   │   ├── progress_tracker.py # Real-time progress tracking
│   │   ├── celery_app.py     # Celery configuration
│   │   └── auto_model_downloader.py # Automatic model downloads
│   └── tests/                # Backend test suite
├── web/                       # React frontend application
│   ├── src/                  # Source code
│   │   ├── components/       # React components
│   │   ├── pages/           # Route-based pages
│   │   ├── lib/             # Utilities and API client
│   │   ├── hooks/           # Custom React hooks
│   │   └── providers/       # Context providers
│   ├── dist/                # Production build output
│   ├── public/              # Static assets
│   └── package.json         # Frontend dependencies
├── projects/                 # ComfyUI project installations (gitignored)
├── models/                   # Shared model storage (gitignored)
├── templates/                # Workflow templates
├── assets/                   # Project assets and images
├── .claude/                  # Claude Code PM configuration
│   ├── context/             # Project context documentation
│   ├── scripts/             # PM automation scripts
│   └── rules/               # Development rules
└── launcher.py              # Main entry point
```

## Key Directories

### Backend Structure (`backend/src/`)
- **API Layer**: Flask routes for project management
- **Task Processing**: Celery workers for async operations
- **Model Management**: Automatic discovery and downloading
- **WebSocket**: Real-time communication via SocketIO
- **Templates**: ComfyUI workflow templates

### Frontend Structure (`web/src/`)
- **components/**: Reusable UI components
  - ImportWorkflowUI.tsx
  - ProjectCard.tsx
  - ModelManager.tsx
  - LiveLogViewer.tsx
  - StorageIndicator.tsx
- **pages/**: Route components
  - index.tsx (main dashboard)
  - import/page.tsx
  - new/page.tsx
  - settings/page.tsx
- **lib/**: Core utilities
  - api.ts (API client)
  - socket.ts (WebSocket client)
  - types.ts (TypeScript definitions)

### Configuration Files
- `package.json` - Root package for build scripts
- `web/package.json` - Frontend dependencies
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Python project configuration
- `config.json` - Application configuration

### Build and Deploy
- `launcher.py` - Main application entry
- `build_and_restart.sh` - Build automation
- `restart_server.sh` - Server restart utility
- `Dockerfile` - Container configuration
- `nginx.conf` - Reverse proxy setup

### Testing Infrastructure
- Extensive test files for various scenarios
- Puppeteer browser automation tests
- Python pytest suite
- React Vitest configuration

## File Naming Conventions

### Backend
- Snake_case for Python files: `model_finder.py`
- Descriptive names for functionality
- Test files prefixed with `test_`

### Frontend
- PascalCase for React components: `ProjectCard.tsx`
- camelCase for utilities: `api.ts`
- Kebab-case for CSS modules
- Page components in route directories

## Special Directories

### Generated/Runtime
- `.celery/` - Celery message broker
- `launcher_venv/` - Python virtual environment
- `node_modules/` - NPM dependencies
- `comfyui_launcher.egg-info/` - Python package info

### Claude Code PM Integration
- `.claude/` - PM system configuration
- Git worktree support planned
- Issue-driven development structure

## Migration Notes

The project appears to be undergoing a major restructure:
- `server/` directory (old structure) → `backend/src/` (new structure)
- All server code has been reorganized
- Frontend components have been updated
- Extensive test suite added