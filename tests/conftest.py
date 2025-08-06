"""
Shared test fixtures and configuration for uQCme tests.

This module contains pytest fixtures that are shared across
all test modules in the uQCme test suite.
"""

import pytest
import pandas as pd
import yaml
from pathlib import Path


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def test_fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config(test_fixtures_dir):
    """Load test configuration file."""
    config_path = test_fixtures_dir / "config_example.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def test_data_paths(test_data_dir):
    """Return dictionary of test data file paths."""
    return {
        'example_run_data': test_data_dir / "example_run_data.tsv",
        'qc_rules': test_data_dir / "QC_rules.tsv",
        'qc_tests': test_data_dir / "QC_tests.tsv",
        'mapping': test_data_dir / "mapping.yaml"
    }


@pytest.fixture
def sample_run_data(test_data_paths):
    """Load sample run data for testing."""
    return pd.read_csv(test_data_paths['example_run_data'], sep='\t')


@pytest.fixture
def qc_rules_data(test_data_paths):
    """Load QC rules data for testing."""
    return pd.read_csv(test_data_paths['qc_rules'], sep='\t')


@pytest.fixture
def qc_tests_data(test_data_paths):
    """Load QC tests data for testing."""
    return pd.read_csv(test_data_paths['qc_tests'], sep='\t')


@pytest.fixture
def mapping_config(test_data_paths):
    """Load mapping configuration for testing."""
    with open(test_data_paths['mapping'], 'r') as f:
        return yaml.safe_load(f)
