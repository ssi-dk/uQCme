# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project structure for uQCme - Microbial QC Reporter v0.1.0
- Configuration system using `config.yaml` for app settings and file paths
- Input data structure with example files:
  - `run_data.tsv`: Sequencing run data metrics with 99 samples
  - `mapping.yaml`: Column mapping and display configuration
  - `QC_rules.tsv`: Quality control rules with 365+ validation criteria
  - `QC_tests.tsv`: QC test outcomes with pass/warning/fail criteria
- Project documentation structure with PLAN.md outlining architecture
- Logging system configuration pointing to `./log/log.tsv`
- Output directory structure for generated reports
- **Comprehensive test suite following Python best practices**:
  - Organized tests directory with proper package structure (`__init__.py` files)
  - Separated unit tests (`tests/unit/`) and integration tests (`tests/integration/`)
  - Test data organization (`tests/data/` and `tests/fixtures/`)
  - Shared pytest fixtures in `tests/conftest.py`
  - 22 comprehensive tests (16 integration + 6 unit tests) all passing
  - Unit tests for individual QCProcessor methods and components
  - End-to-end integration tests validating complete QC workflows
  - Synthetic test dataset with 30 samples covering diverse QC scenarios

### Changed

- **Code quality improvements and refactoring**:
  - Extracted filter creation methods from `render_sidebar_filters()` for better modularity
  - Added `_create_numerical_filter()`, `_create_categorical_filter()`, and `_create_text_search_filter()` methods
  - Created reusable `_render_plotly_chart()` helper to eliminate code duplication
  - Added `_render_styled_dataframe()` method for consistent DataFrame rendering
  - **Moved hardcoded constants to configurable YAML settings**:
    - `categorical_filter_threshold`: Controls when to use dropdown vs text search (default: 20)
    - `section_toggle_columns`: Number of columns for section toggles (default: 3)
    - `max_displayed_rules`: Maximum rules shown in sample details (default: 10)
    - Added `_get_dashboard_config()` helper for config value retrieval with fallbacks
  - Reduced function complexity: `render_sidebar_filters()` now 50% shorter and more readable
  - Eliminated repetitive Plotly chart rendering patterns across all visualization tabs
  - Improved type annotations with `Optional` for better code documentation
  - Enhanced maintainability through method extraction and consistent patterns
- **Enhanced UI layout and space optimization**:
  - Moved version, sample count, and QC metrics from main header to sidebar
  - Created dedicated `render_sidebar_metrics()` method for summary statistics
  - Significantly increased available space for data tables and visualizations
  - Improved information organization with logical grouping of filters and metrics
- **Fixed NaN handling in numerical filters**:
  - Resolved issue where samples with missing values in numerical columns were incorrectly filtered out
  - Range sliders now preserve NaN values when set to full range (no filtering applied)
  - Partial range filtering includes NaN values to prevent data loss
  - Now correctly shows all 97/97 samples when no filters are applied
- **Reorganized test directory structure according to Python best practices**:
  - Moved test data files to organized subdirectories (`data/`, `fixtures/`)
  - Created proper Python package structure with `__init__.py` files
  - Separated unit and integration tests into dedicated directories
  - Updated all test file paths and configuration to match new structure
  - Created `tests/README.md` with comprehensive documentation of test organization
  - Added shared pytest fixtures for better test maintainability
  - Enhanced test coverage with both unit tests and integration tests
- **Implemented comprehensive logging system**:
  - Replaced print statements with proper logging using Python's logging module
  - Added TSV-format log file output to location specified in `config.yaml`
  - Dual output: structured logs to file, readable format to console
  - Log levels: INFO for normal operations, WARNING for issues, ERROR for failures
  - Timestamp and log level tracking for better debugging and monitoring
  - Updated `.gitignore` to include comprehensive Python development patterns
- Restructured project for PyPI deployment:
  - Moved source code to `src/uQCme` directory
  - Renamed `uQCme.py` to `cli.py`
  - Added `pyproject.toml` and `MANIFEST.in`
  - Updated imports to use relative paths within the package
- Refactored data loading logic into `utils.py` to support API data loading in both CLI and App
- Refactored configuration loading logic into `utils.py` to be shared between CLI and App
- Updated README.md with correct usage instructions for `uqcme` and `uqcme-dashboard` commands
  - Implemented Streamlit launcher in `app.py` to support `uqcme-dashboard` entry point

### Fixed

- Fixed an issue where the dashboard would stop execution instead of offering a file upload option when the configured data file is missing or empty.

### In Progress

- [x] Implement `uQCme.py` CLI tool for QC processing (COMPLETED)
  - [x] Dynamic field mapping from configuration
  - [x] Species/assembly type/software filtering
  - [x] QC overrides system with case-insensitive matching
  - [x] Comprehensive rule evaluation and outcome determination
  - [x] Unique warning collection and summary reporting
- [x] Create comprehensive test input data (`./input/example/example_run_data.tsv`)
  - [x] Generated synthetic microbial sequencing data designed to trigger specific QC outcomes
  - [x] Included samples that will PASS, WARN, and FAIL different QC rules and tests
  - [x] Covered multiple species types, assembly types, and software combinations
  - [x] Ensured data includes realistic values for all mapped fields (GC, N50, contigs, completeness, contamination, etc.)
  - [x] Validated that test data triggers expected outcomes across QC tests
  - [x] Test data successfully demonstrates rule filtering logic and QC outcome determination
- [x] **Create unit tests**
  - [x] Unit tests for QCProcessor class methods (operator logic, field mapping, rule matching)
  - [x] Integration tests for complete QC processing workflows
  - [x] Test data integrity validation
  - [x] Organized test structure following Python best practices
  - [x] 22 tests covering all major functionality (100% passing)

### Pending Tasks

- [x] Implement `app.py` Streamlit web application (COMPLETED)
  - [x] Created comprehensive Streamlit dashboard for QC data visualization
  - [x] Modularized plotting functionality into separate `plot.py` library
  - [x] Implemented data filtering and interactive exploration features
  - [x] Added QC outcomes visualization, species distribution, and failed rules analysis
  - [x] Quality metrics visualization with distribution, box plots, and scatter plots
  - [x] Sample detail views with individual QC rule analysis
  - [x] Data export functionality with CSV/TSV download options
  - [x] Fixed Streamlit duplicate element ID issues with unique keys
- [x] Implement `plot.py` plotting module (COMPLETED)
  - [x] Created QCPlotter class with comprehensive plotting functionality
  - [x] Implemented pie charts, bar charts, histograms, box plots, and scatter plots
  - [x] Added correlation heatmaps and overview dashboard generation
  - [x] Integrated with Streamlit app for seamless visualization
  - [x] Data export functionality (CSV/TSV formats)
  - [x] Responsive multi-tab interface with sidebar filtering
- [x] Implement `plot.py` plotting module (COMPLETED)
  - [x] Extracted all plotting logic from app.py into dedicated plotting library
  - [x] Created QCPlotter class with comprehensive visualization methods
  - [x] Pie charts for QC outcome distribution
  - [x] Bar charts for species and failed rules analysis
  - [x] Distribution plots, box plots, and scatter plots for quality metrics
  - [x] Correlation heatmaps for multi-metric analysis
  - [x] Color mapping system using configuration-based themes
  - [x] Quality overview dashboard with integrated plot collections
- [ ] Create sample selection and filtering functionality (COMPLETED via Streamlit interface)
- [ ] Implement QC rule processing engine (COMPLETED via CLI integration)
- [ ] Add data visualization components (COMPLETED via plot.py)
- [ ] Implement API integration for sample handling
- [ ] Add comprehensive error handling and validation
- [ ] Add user documentation and examples

### Architecture Overview

The project follows a modular architecture:

1. **CLI Component** (`uQCme.py`): Data processing and QC rule evaluation
2. **Web Interface** (`app.py`): Interactive Streamlit dashboard
3. **Visualization** (`plot.py`): Chart and graph generation
4. **Configuration**: YAML-based settings management
5. **Data Flow**: TSV → Processing → Results → Visualization

---

## Project Structure

```text
uQCme/
├── config.yaml              # Main configuration
├── src/
│   └── uQCme/
│       ├── __init__.py      # Package initialization
│       ├── cli.py           # CLI QC processor (COMPLETED)
│       ├── app.py           # Streamlit web app (COMPLETED)
│       └── plot.py          # Plotting utilities (COMPLETED)
├── requirements.txt         # Python dependencies
├── input/example/           # Sample data files
│   ├── run_data.tsv        # Sequencing metrics (cleaned)
│   ├── mapping.yaml        # Column mappings
│   ├── QC_rules.tsv       # Quality control rules
│   └── QC_tests.tsv       # QC outcome definitions
├── output/                 # Generated results
├── log/                   # Application logs
└── tests/                 # Comprehensive test suite
    ├── __init__.py         # Package structure
    ├── conftest.py         # Shared pytest fixtures
    ├── README.md           # Test documentation
    ├── data/               # Test data files
    │   ├── example_run_data.tsv
    │   ├── mapping.yaml
    │   ├── QC_rules.tsv
    │   └── QC_tests.tsv
    ├── fixtures/           # Test configuration files
    │   └── config_example.yaml
    ├── integration/        # End-to-end tests
    │   ├── __init__.py
    │   └── test_uQCme_outcomes.py
    └── unit/               # Component tests
        ├── __init__.py
        └── test_qc_processor.py
```

---

*This changelog tracks both completed work and planned development for the uQCme project.*
