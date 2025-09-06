# Contributing to ComfyUI Launcher

Thank you for your interest in contributing to ComfyUI Launcher! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/comfyui-launcher.git`
3. Add upstream remote: `git remote add upstream https://github.com/comfyui-launcher/comfyui-launcher.git`
4. Create a feature branch: `git checkout -b feature/your-feature-name`

## Development Setup

```bash
# Install all dependencies
npm install
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run development servers
npm run dev
```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Use meaningful variable names

```python
def calculate_download_progress(
    downloaded_bytes: int,
    total_bytes: int
) -> float:
    """Calculate download progress as a percentage.
    
    Args:
        downloaded_bytes: Number of bytes downloaded
        total_bytes: Total file size in bytes
        
    Returns:
        Progress percentage (0-100)
    """
    if total_bytes == 0:
        return 0.0
    return (downloaded_bytes / total_bytes) * 100
```

### TypeScript (Frontend)

- Use TypeScript for all new code
- Define interfaces for all data structures
- Avoid `any` type - use `unknown` if type is truly unknown
- Use functional components with hooks
- Keep components small and composable

```typescript
interface ProgressBarProps {
  value: number;
  max: number;
  label?: string;
}

export function ProgressBar({ value, max, label }: ProgressBarProps) {
  const percentage = (value / max) * 100;
  
  return (
    <div className="progress-bar">
      {label && <span>{label}</span>}
      <div 
        className="progress-bar-fill"
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes that don't modify src or test files

### Examples

```bash
feat(api): add model search endpoint

Add POST /api/search/models endpoint that uses AI to find
missing models across multiple sources.

Closes #123

---

fix(ui): resolve React hooks error in ImportWorkflowUI

Move state declarations before conditional returns to comply
with React's rules of hooks.

---

docs: update installation instructions for Windows

Add specific instructions for Windows users including
PowerShell commands and path configuration.
```

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest backend/tests/test_utils.py

# Run with coverage
pytest --cov=backend.src

# Run specific test
pytest -k "test_download_file"
```

### Frontend Tests

```bash
# Run all tests
cd web && npm test

# Run in watch mode
cd web && npm run test:watch

# Run with coverage
cd web && npm run test:coverage
```

### Writing Tests

- Write tests for all new features
- Maintain test coverage above 70%
- Use descriptive test names
- Test edge cases and error conditions
- Mock external dependencies

```python
def test_model_download_retry_on_failure(mock_requests):
    """Test that download retries on network failure."""
    # Arrange
    mock_requests.get.side_effect = [
        requests.ConnectionError("Network error"),
        Mock(status_code=200, content=b"model data")
    ]
    
    # Act
    result = download_model("http://example.com/model.bin", "model.bin")
    
    # Assert
    assert result.success is True
    assert mock_requests.get.call_count == 2
```

## Pull Request Process

1. Update your branch with latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Ensure all tests pass:
   ```bash
   npm test
   npm run lint
   ```

3. Update documentation if needed

4. Create a pull request with:
   - Clear title following commit convention
   - Description of changes
   - Link to related issues
   - Screenshots for UI changes

5. Wait for review and address feedback

## Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated for new functionality
- [ ] Documentation updated if needed
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main
- [ ] All CI checks pass

## Architecture Decisions

### Backend Structure

```
backend/
├── src/
│   ├── api/          # REST API endpoints
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   ├── tasks/        # Celery tasks
│   └── utils/        # Utility functions
└── tests/
    ├── unit/         # Unit tests
    └── integration/  # Integration tests
```

### Frontend Structure

```
web/src/
├── components/       # React components
├── hooks/           # Custom React hooks
├── lib/             # Utilities and helpers
├── pages/           # Page components
└── styles/          # Global styles
```

## Release Process

1. Update version in `package.json` and `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. After merge, tag release: `git tag v0.1.0`
5. Push tag: `git push origin v0.1.0`

## Getting Help

- Check existing issues and discussions
- Join our Discord server
- Read the documentation
- Ask in pull request comments

## Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes
- Project website

Thank you for contributing to ComfyUI Launcher!