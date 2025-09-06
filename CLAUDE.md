# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyUI-Launcher is a bulletproof dependency management tool for ComfyUI workflows. It consists of:
- Flask backend with Celery for async task processing
- React frontend with Vite, TypeScript, and TailwindCSS
- WebSocket support for real-time updates
- Automatic model downloading and management
- Project isolation with virtual environments

## Architecture Overview

### Backend Architecture
- **Main Entry**: `launcher.py` - Flask application entry point
- **Server**: `backend/src/server.py` - Flask server with SocketIO for real-time communication
- **API Endpoints**: RESTful API for project management, model handling, and workflow operations
- **Async Tasks**: `backend/src/tasks.py` - Celery tasks for background processing
- **Model Management**: `backend/src/model_finder.py` - Automatic model discovery and downloading
- **Progress Tracking**: `backend/src/progress_tracker.py` - Real-time progress updates via WebSocket

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: React Router v6 with pages in `web/src/pages/`
- **State Management**: TanStack Query (React Query) for server state
- **UI Components**: Custom components with Radix UI primitives and TailwindCSS
- **Real-time Updates**: Socket.IO client for WebSocket connections
- **Theme**: Dark/light mode support with next-themes

## Common Development Commands

### Setup and Installation
```bash
# Install all dependencies (backend + frontend)
npm install

# Create Python virtual environment (if needed)
python -m venv launcher_venv
source launcher_venv/bin/activate  # On Windows: launcher_venv\Scripts\activate
pip install -r requirements.txt
```

### Development
```bash
# Run both backend and frontend in development mode
npm run dev

# Run backend only
npm run dev:backend
# Or directly: python launcher.py

# Run frontend only
npm run dev:frontend
# Or: cd web && npm run dev
```

### Building
```bash
# Build frontend for production
npm run build

# Build and restart server (useful for testing production builds)
cd web && npm run build-restart
```

### Testing
```bash
# Run all tests
npm test

# Backend tests only
npm run test:backend
# Or: pytest

# Frontend tests only
npm run test:frontend
# Or: cd web && npm test

# Frontend tests with watch mode
cd web && npm run test:watch

# Frontend tests with coverage
cd web && npm run test:coverage
```

### Code Quality
```bash
# Run all linters
npm run lint

# Backend linting
npm run lint:backend
# Or: ruff check backend/

# Frontend linting
npm run lint:frontend
# Or: cd web && npm run lint

# Format all code
npm run format

# Backend formatting
npm run format:backend
# Or: black backend/ && ruff check --fix backend/

# Frontend formatting
npm run format:frontend
# Or: cd web && npm run format

# TypeScript type checking
cd web && npm run typecheck
```

### Cleanup
```bash
# Remove all build artifacts and dependencies
npm run clean
```

## Key API Endpoints

- `GET /api/projects` - List all projects
- `POST /api/create_project` - Create new project with virtual environment
- `POST /api/import_project` - Import workflow from URL or file
- `GET /api/storage/usage` - Get model storage statistics
- `GET /api/models` - List all downloaded models
- WebSocket events: `progress_update`, `log_entry` for real-time updates

## Important Project Rules

1. **Claude Code PM Integration**: This project uses Claude Code PM system. Use PM commands when available.
2. **Virtual Environments**: Each ComfyUI project gets its own isolated Python environment
3. **Model Management**: Models are shared across projects but tracked per-project
4. **Port Management**: Projects use ports in range 4001-4100 (configurable)
5. **Error Handling**: All errors should provide actionable suggestions to users

## File Organization

- `/backend/src/` - Python backend code
- `/web/src/` - React frontend code
- `/web/src/components/` - Reusable React components
- `/web/src/pages/` - Route-based page components
- `/web/src/lib/` - Utilities and API client
- `/projects/` - ComfyUI project installations (gitignored)
- `/models/` - Shared model storage (gitignored)

## Testing Approach

- Backend: pytest with real service testing (no mocks)
- Frontend: Vitest with React Testing Library
- E2E: Puppeteer/Playwright scripts for workflow testing
- Always verify tests pass before committing

## Development Tips

1. The backend serves the frontend's built files in production
2. Use `npm run dev` to run both frontend and backend with hot-reload
3. Check `backend/src/API_DOCUMENTATION.md` for detailed API specs
4. WebSocket subscriptions are project-specific for efficient updates
5. Frontend uses absolute imports via `@/` alias for src directory

## Control Loop
- Treat GitHub Issues as the single source of truth.
- Iterate on tasks via CCPM only; never bypass with ad-hoc edits.
- One git worktree/branch per issue; no mixed changes.
- If blocked, label "blocked", post blockers, then run `/pm:blocked` and move on.
- Close items only after acceptance criteria + tests + merged PR + issue comment proof.
