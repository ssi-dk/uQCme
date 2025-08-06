# uQCme Test Suite

This directory contains the comprehensive test suite for uQCme, organized according to Python testing best practices.

## Directory Structure

```
tests/
├── __init__.py              # Makes tests a Python package
├── conftest.py             # Shared pytest fixtures
├── README.md               # This file
├── data/                   # Test data files
│   ├── example_run_data.tsv
│   ├── mapping.yaml
│   ├── QC_outcomes.tsv
│   ├── QC_rules.tsv
│   └── run_stats.tsv
├── fixtures/               # Test configuration files
│   └── config_example.yaml
├── integration/            # Integration tests
│   ├── __init__.py
│   └── test_uQCme_outcomes.py
└── unit/                   # Unit tests
    ├── __init__.py
    └── test_qc_processor.py
```

## Test Categories

### Unit Tests (`unit/`)
Tests for individual components and methods in isolation:
- `test_qc_processor.py`: Tests for QCProcessor class methods
  - Configuration loading
  - Operator application logic
  - Field mapping functionality
  - Rule matching criteria

### Integration Tests (`integration/`)
Tests for complete workflows and system interactions:
- `test_uQCme_outcomes.py`: End-to-end testing of QC processing
  - 16 comprehensive test cases
  - Tests all QC outcome categories
  - Validates data integrity
  - Tests species-specific rules

## Test Data

### Synthetic Test Dataset (`data/`)
- **30 synthetic samples** with diverse characteristics
- **363 QC rules** covering various scenarios
- **11 outcome categories** (PASS, contamination, coverage, etc.)
- **Species coverage**: E. coli, Salmonella, Listeria, etc.

### Test Configuration (`fixtures/`)
- `config_example.yaml`: Test-specific configuration
- Paths adjusted for test directory structure
- Simplified for testing scenarios

## Running Tests

### All Tests
```bash
# From project root
python -m pytest tests/ -v
```

### Unit Tests Only
```bash
python -m pytest tests/unit/ -v
```

### Integration Tests Only
```bash
python -m pytest tests/integration/ -v
```

### Specific Test File
```bash
python -m pytest tests/integration/test_uQCme_outcomes.py -v
```

### With Coverage
```bash
python -m pytest tests/ --cov=uQCme --cov-report=html
```

## Shared Fixtures

The `conftest.py` file provides shared fixtures available to all tests:

- `test_data_dir`: Path to test data directory
- `sample_config`: Loaded test configuration
- `test_data_paths`: Dictionary of test data file paths

## Test Development Guidelines

### Adding New Unit Tests
1. Create test files in `tests/unit/`
2. Follow naming convention: `test_<module_name>.py`
3. Test individual methods/functions in isolation
4. Use `unittest.TestCase` or pytest style

### Adding New Integration Tests
1. Create test files in `tests/integration/`
2. Test complete workflows
3. Use real test data from `tests/data/`
4. Focus on end-to-end scenarios

### Test Data Management
- Keep test data in `tests/data/`
- Use realistic but synthetic data
- Document data characteristics
- Keep file sizes reasonable

## Best Practices

1. **Isolation**: Unit tests should not depend on external files
2. **Deterministic**: Tests should produce consistent results
3. **Fast**: Unit tests should run quickly
4. **Clear**: Test names should describe what they test
5. **Coverage**: Aim for high code coverage
6. **Fixtures**: Use shared fixtures for common setup

## Dependencies

Tests require:
- `pytest`: Test framework
- `pandas`: Data manipulation
- `pyyaml`: YAML configuration loading
- `pathlib`: Path handling

Install test dependencies:
```bash
pip install pytest pytest-cov
```

## Continuous Integration

This test suite is designed to run in CI/CD environments:
- All paths are relative to project root
- No external dependencies required
- Comprehensive coverage of functionality
- Fast execution time

## Troubleshooting

### Import Issues
If you see import errors, ensure you're running tests from the project root:
```bash
cd /path/to/uQCme
python -m pytest tests/
```

### Path Issues
All test data paths are configured relative to the tests directory. If tests fail due to file not found errors, check that:
1. Test data files exist in `tests/data/`
2. Configuration files reference correct paths
3. Working directory is project root

### Missing Dependencies
Install required packages:
```bash
pip install pandas pyyaml pytest
```
