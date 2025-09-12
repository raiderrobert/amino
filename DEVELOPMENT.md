# Development Guide

This guide covers development setup, testing, and contribution guidelines for amino.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Clone and Install

```bash
git clone https://github.com/yourusername/amino.git
cd amino
make install-dependencies
```

This project uses `uv` for dependency management and includes a Makefile for common development tasks. The install command sets up all development dependencies including:
- pytest for testing
- pytest-cov for coverage reporting
- ruff for linting and formatting
- ty for type checking

## Project Structure

```
amino/
├── amino/              # Main package source code
├── tests/              # Test files
├── examples/           # Example schemas and usage
├── pyproject.toml      # Project configuration
├── README.md           # User documentation
└── DEVELOPMENT.md      # This file
```

## Development Workflow

### Code Quality

The project uses a Makefile for common development tasks:

**Linting and Formatting**
```bash
make tidy              # Format code with ruff and type check with ty
```

**Update Dependencies**
```bash
make upgrade-dependencies  # Upgrade all dependencies
```

### Running Tests

```bash
# Run all tests with coverage
make test

# Or run pytest directly
uv run pytest

# Run specific test file
uv run pytest tests/test_specific.py

# Run with verbose output
uv run pytest -v
```

### Code Style

- Line length: 120 characters
- Use ruff for formatting and linting
- Follow PEP 8 guidelines
- Add type hints where appropriate

## Contributing

### Before Submitting

1. Ensure all tests pass
2. Run linting and formatting tools
3. Add tests for new functionality
4. Update documentation if needed

### Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Add/update tests
5. Ensure all checks pass
6. Submit a pull request

## Testing Guidelines

- Write tests for all new features
- Maintain good test coverage
- Use descriptive test names
- Test both success and error cases
- Include integration tests for complex features

## Release Process

Releases are managed through the project's CI/CD pipeline. Version numbers follow semantic versioning (semver).