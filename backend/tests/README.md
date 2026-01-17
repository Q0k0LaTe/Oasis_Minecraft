# Tests for Minecraft Mod Generator Backend

## Overview

This directory contains unit and integration tests for the mod generation pipeline.

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/agents/test_pipeline.py
```

### Run with verbose output
```bash
pytest -v
```

### Run tests matching a pattern
```bash
pytest -k "test_compiler"
```

## Test Structure

```
tests/
├── __init__.py
├── README.md
└── agents/
    ├── __init__.py
    ├── test_pipeline.py       # Pipeline integration tests
    ├── test_compiler.py       # Compiler unit tests
    ├── test_spec_manager.py   # SpecManager unit tests
    └── test_tools.py          # Tool unit tests
```

## Test Categories

### Unit Tests
- **test_compiler.py**: Tests Spec → IR transformation
- **test_spec_manager.py**: Tests spec persistence and versioning
- **test_tools.py**: Tests individual tool implementations

### Integration Tests
- **test_pipeline.py**: Tests end-to-end pipeline execution

## Writing New Tests

When adding new tests:
1. Create test file in appropriate directory
2. Use pytest fixtures for setup/teardown
3. Follow naming convention: `test_<component>.py`
4. Document what each test verifies

## Requirements

```bash
pip install pytest pytest-cov
```

## Coverage

Run tests with coverage:
```bash
pytest --cov=agents --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```
