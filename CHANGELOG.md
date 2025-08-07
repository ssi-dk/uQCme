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
├── uQCme.py                 # CLI QC processor (COMPLETED)
├── app.py                   # Streamlit web app (COMPLETED)
├── plot.py                  # Plotting utilities (COMPLETED)
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
