---
created: 2025-09-06T20:01:08Z
last_updated: 2025-09-06T20:01:08Z
version: 1.0
author: Claude Code PM System
---

# Project Style Guide

## Code Style Guidelines

### Python Style (Backend)

#### Naming Conventions
- **Files**: Snake_case (`model_finder.py`, `progress_tracker.py`)
- **Classes**: PascalCase (`ModelFinder`, `WorkflowValidator`)
- **Functions**: Snake_case (`get_project_port`, `update_progress`)
- **Constants**: UPPER_SNAKE_CASE (`SERVER_PORT`, `MODELS_DIR`)
- **Private**: Leading underscore (`_internal_method`)

#### Code Organization
```python
# Standard import order
import os
import sys
from typing import Dict, List, Optional

import third_party_package
from flask import Flask, jsonify

from local_module import local_function
```

#### Documentation
```python
def process_workflow(workflow_json: Dict, validate: bool = True) -> Dict:
    """Process a ComfyUI workflow JSON.
    
    Args:
        workflow_json: The workflow dictionary to process
        validate: Whether to validate before processing
        
    Returns:
        Processed workflow with metadata
        
    Raises:
        ValidationError: If workflow is invalid
    """
```

#### Error Handling
```python
# Provide actionable error messages
try:
    result = download_model(url)
except DownloadError as e:
    return {
        "error": str(e),
        "type": "DownloadError",
        "suggestions": [
            "Check your internet connection",
            "Verify the model URL is correct",
            "Try again later"
        ]
    }
```

### TypeScript/React Style (Frontend)

#### Naming Conventions
- **Components**: PascalCase (`ProjectCard.tsx`, `ModelManager.tsx`)
- **Utilities**: camelCase (`utils.ts`, `api.ts`)
- **Hooks**: camelCase with 'use' prefix (`useWebSocket.ts`)
- **Types**: PascalCase (`ProjectData`, `ModelInfo`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `API_BASE_URL`)

#### Component Structure
```tsx
// Functional components with TypeScript
interface ProjectCardProps {
  project: Project;
  onLaunch: (id: string) => void;
  className?: string;
}

export function ProjectCard({ project, onLaunch, className }: ProjectCardProps) {
  // Hooks first
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  
  // Event handlers
  const handleLaunch = useCallback(() => {
    // Implementation
  }, [project.id]);
  
  // Render
  return (
    <Card className={cn("p-4", className)}>
      {/* Component content */}
    </Card>
  );
}
```

#### Import Organization
```tsx
// External imports first
import React, { useState, useCallback } from 'react';
import { Card } from '@radix-ui/react-card';

// Internal imports
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

// Types
import type { Project } from '@/lib/types';
```

### CSS/Styling Conventions

#### TailwindCSS Classes
```tsx
// Use cn() utility for conditional classes
<div className={cn(
  "flex items-center gap-4 p-4",
  "hover:bg-gray-100 dark:hover:bg-gray-800",
  isActive && "bg-blue-50 dark:bg-blue-900",
  className
)}>
```

#### Component Styling Priority
1. Tailwind utilities for common styles
2. CSS modules for complex component-specific styles
3. Inline styles only for dynamic values

### File Structure Conventions

#### Backend Files
```
backend/src/
├── server.py           # Main application file
├── tasks.py           # Async task definitions
├── models/            # Data models
├── utils/             # Utility functions
├── validators/        # Input validation
└── tests/            # Test files
```

#### Frontend Files
```
web/src/
├── components/
│   ├── ui/           # Base UI components
│   └── ProjectCard.tsx # Feature components
├── pages/            # Route pages
├── hooks/            # Custom hooks
├── lib/              # Utilities
└── types/            # TypeScript types
```

### Git Commit Conventions

#### Commit Message Format
```
type(scope): subject

body (optional)

footer (optional)
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting)
- `refactor`: Code refactor
- `test`: Test additions/changes
- `chore`: Build/tooling changes

#### Examples
```
feat(import): add drag-and-drop support for workflow files

fix(models): resolve download retry logic for large files

docs(api): update WebSocket event documentation
```

### Testing Conventions

#### Test File Naming
- Python: `test_*.py` or `*_test.py`
- TypeScript: `*.test.ts` or `*.spec.ts`

#### Test Structure
```python
def test_workflow_import_validates_json():
    """Test that workflow import properly validates JSON structure."""
    # Arrange
    invalid_workflow = {"invalid": "structure"}
    
    # Act
    result = import_workflow(invalid_workflow)
    
    # Assert
    assert result["error"] == "Invalid workflow format"
    assert "suggestions" in result
```

### Documentation Standards

#### Code Comments
- Explain WHY, not WHAT
- Document complex algorithms
- Note any workarounds or hacks
- Reference issues/PRs for context

#### API Documentation
- Document all endpoints
- Include request/response examples
- Note authentication requirements
- List possible error codes

### Security Conventions

1. **Never commit secrets**: Use environment variables
2. **Validate all inputs**: Especially file paths
3. **Sanitize user content**: Prevent XSS
4. **Use HTTPS**: For all external requests
5. **Limit permissions**: Principle of least privilege

### Performance Guidelines

1. **Lazy loading**: Load components as needed
2. **Debounce inputs**: Prevent excessive API calls
3. **Cache responses**: Use React Query caching
4. **Optimize images**: Use appropriate formats
5. **Bundle splitting**: Keep chunks small

### Accessibility Standards

1. **ARIA labels**: For all interactive elements
2. **Keyboard navigation**: Full keyboard support
3. **Color contrast**: WCAG AA compliance
4. **Focus indicators**: Clear focus states
5. **Screen reader**: Test with screen readers