# Contributing to Home Assistant Life Time Fitness

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- A virtual environment tool (venv, virtualenv, or similar)

### Setting Up Your Development Environment

1. **Clone the repository:**

   ```bash
   git clone https://github.com/jsheputis/home-assistant-lifetime-fitness.git
   cd home-assistant-lifetime-fitness
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**

   ```bash
   pre-commit install
   ```

## Code Quality

This project uses several tools to maintain code quality:

- **[Ruff](https://github.com/astral-sh/ruff)** - Fast Python linter and formatter
- **[mypy](https://mypy.readthedocs.io/)** - Static type checker
- **[pre-commit](https://pre-commit.com/)** - Git hooks for code quality checks

### Running Linting

```bash
# Run ruff linter
ruff check .

# Run ruff linter with auto-fix
ruff check --fix .

# Run ruff formatter
ruff format .

# Run mypy type checking
mypy custom_components/
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run them manually:

```bash
pre-commit run --all-files
```

## Testing

This project uses pytest with the `pytest-homeassistant-custom-component` plugin.

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=custom_components/lifetime_fitness --cov-report=term-missing

# Run a specific test file
pytest tests/test_api.py

# Run a specific test
pytest tests/test_api.py::TestApiClient::test_authenticate_success

# Run tests with verbose output
pytest -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Follow the naming convention `test_*.py` for test files
- Use pytest fixtures from `conftest.py` for common test data
- Mock external API calls to avoid network dependencies

Example test structure:

```python
"""Tests for my_module."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.lifetime_fitness.my_module import MyClass


class TestMyClass:
    """Tests for MyClass."""

    def test_something(self) -> None:
        """Test that something works."""
        assert MyClass().method() == expected_value

    async def test_async_method(self) -> None:
        """Test async method."""
        result = await MyClass().async_method()
        assert result is not None
```

## Code Style Guidelines

### Type Hints

- All functions should have type hints for parameters and return values
- Use `from __future__ import annotations` for forward references
- Use `| None` instead of `Optional[]`

```python
from __future__ import annotations

def my_function(param: str, optional_param: int | None = None) -> dict[str, Any]:
    """Function with proper type hints."""
    ...
```

### Docstrings

- All public functions, classes, and modules should have docstrings
- Use Google-style docstrings

```python
def my_function(param: str) -> str:
    """Short description of function.

    Longer description if needed.

    Args:
        param: Description of parameter.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param is invalid.
    """
    ...
```

### Imports

- Group imports in the following order:
  1. Standard library imports
  2. Third-party imports
  3. Local imports
- Use absolute imports for local modules
- Let ruff handle import sorting

### Error Handling

- Create specific exception classes for different error types
- Use exception chaining with `raise ... from err`
- Log errors appropriately before raising

## Pull Request Process

1. **Create a feature branch:**

   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes:**
   - Write tests for new functionality
   - Update documentation if needed
   - Ensure all tests pass
   - Ensure linting passes

3. **Commit your changes:**

   ```bash
   git add .
   git commit -m "Add my new feature"
   ```

4. **Push to your fork:**

   ```bash
   git push origin feature/my-new-feature
   ```

5. **Create a Pull Request:**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure CI checks pass

## Project Structure

```text
home-assistant-lifetime-fitness/
├── custom_components/
│   └── lifetime_fitness/
│       ├── __init__.py        # Integration setup
│       ├── api.py             # API client
│       ├── config_flow.py     # Configuration UI flow
│       ├── const.py           # Constants
│       ├── model.py           # Data models
│       ├── sensor.py          # Sensor entity
│       ├── manifest.json      # Integration manifest
│       ├── strings.json       # UI strings
│       └── translations/      # Translations
├── tests/
│   ├── conftest.py            # Test fixtures
│   ├── test_api.py            # API tests
│   ├── test_config_flow.py    # Config flow tests
│   ├── test_init.py           # Integration setup tests
│   ├── test_model.py          # Data model tests
│   └── test_sensor.py         # Sensor tests
├── .github/workflows/         # CI/CD workflows
├── .pre-commit-config.yaml    # Pre-commit configuration
├── pyproject.toml             # Project configuration
└── README.md                  # Project documentation
```

## Reporting Issues

When reporting issues, please include:

- Home Assistant version
- Integration version
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Relevant log entries

## Questions?

If you have questions, feel free to open an issue on GitHub.
