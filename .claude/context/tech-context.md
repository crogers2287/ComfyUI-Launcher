---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# Technology Context

## Technology Stack

### Backend Technologies
- **Language**: Python 3.12
- **Web Framework**: Flask 3.0.2
- **Async Tasks**: Celery 5.3.6
- **WebSocket**: Flask-SocketIO 5.3.6 / python-socketio 5.11.0
- **Process Management**: psutil 5.9.8
- **HTTP Client**: requests 2.31.0
- **File Management**: show-in-file-manager 1.1.4

### Frontend Technologies
- **Framework**: React 18.2.0
- **Language**: TypeScript 5.2.2
- **Build Tool**: Vite 5.1.4
- **Routing**: React Router DOM 6.22.1
- **State Management**: TanStack Query 5.24.1
- **UI Components**: Radix UI primitives
- **Styling**: TailwindCSS 3.4.1
- **WebSocket Client**: socket.io-client 4.8.1
- **Theme**: next-themes 0.2.1

### Development Tools
- **Python Linting**: ruff
- **Python Formatting**: black
- **Frontend Linting**: ESLint 8.56.0
- **Frontend Formatting**: Prettier 3.2.5
- **Testing (Backend)**: pytest
- **Testing (Frontend)**: Vitest 3.2.4
- **E2E Testing**: Puppeteer 24.17.1 / Playwright 1.55.0
- **Pre-commit**: pre-commit 3.6.2

## Key Dependencies

### Python Dependencies (requirements.txt)
```
Flask==3.0.2
Flask-SocketIO==5.3.6
celery==5.3.6
torch==2.2.1
numpy==1.26.4
tqdm==4.66.2
PyYAML==6.0.1
virtualenv==20.25.1
```

### Frontend Dependencies
```
@tanstack/react-query: ^5.24.1
@radix-ui/react-*: Various UI primitives
tailwindcss: ^3.4.1
lucide-react: ^0.340.0 (icons)
sonner: ^1.4.3 (toast notifications)
react-dropzone: ^14.2.3 (file uploads)
```

## Development Environment

### Node.js
- Required version: >=20.0.0
- NPM version: >=10.0.0

### Python
- Virtual environment: launcher_venv
- Package manager: pip

### Build System
- Frontend bundler: Vite with React plugin
- TypeScript compilation: tsc
- CSS processing: PostCSS with Tailwind

## Architecture Patterns

### Backend Architecture
- RESTful API design
- Async task processing with Celery
- WebSocket for real-time updates
- File-system based message broker for Celery
- Model management with automatic downloading

### Frontend Architecture
- Component-based React architecture
- TypeScript for type safety
- TanStack Query for server state
- Radix UI for accessible components
- CSS-in-JS with Tailwind utilities
- Dark/light theme support

## External Services Integration

### Model Sources
- CivitAI integration
- Hugging Face model support
- URL-based model downloads
- Automatic dependency resolution

### ComfyUI Integration
- Virtual environment isolation per project
- Port management (4001-4100 range)
- Workflow JSON processing
- Custom node installation support

## Testing Infrastructure

### Backend Testing
- pytest for unit and integration tests
- Real service testing (no mocks policy)
- Test files for model detection, imports, workflows

### Frontend Testing
- Vitest for unit tests
- React Testing Library
- Puppeteer for E2E tests
- Multiple browser automation test files

## Development Scripts

### NPM Scripts (root)
- `npm install`: Install all dependencies
- `npm run dev`: Run full stack development
- `npm run build`: Build frontend
- `npm test`: Run all tests
- `npm run lint`: Lint all code
- `npm run format`: Format all code

### NPM Scripts (web/)
- `npm run dev`: Vite dev server
- `npm run build`: TypeScript + Vite build
- `npm run test:watch`: Vitest watch mode
- `npm run typecheck`: TypeScript checking

## Configuration Files

### Build Configuration
- `vite.config.ts`: Vite bundler config
- `tsconfig.json`: TypeScript configuration
- `tailwind.config.js`: Tailwind CSS setup
- `postcss.config.js`: PostCSS processing

### Development Configuration
- `.pre-commit-config.yaml`: Git hooks
- `pyproject.toml`: Python project metadata
- `components.json`: UI component configuration