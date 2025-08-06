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

### In Progress

- [x] Implement `uQCme.py` CLI tool for QC processing (COMPLETED)
  - [x] Dynamic field mapping from configuration
  - [x] Species/assembly type/software filtering
  - [x] QC overrides system with case-insensitive matching
  - [x] Comprehensive rule evaluation and outcome determination
  - [x] Unique warning collection and summary reporting

### Pending Tasks

- [x] Create comprehensive test input data (`./input/example/example_run_data.tsv`)
  - [x] Generated synthetic microbial sequencing data designed to trigger specific QC outcomes
  - [x] Included samples that will PASS, WARN, and FAIL different QC rules and tests
  - [x] Covered multiple species types, assembly types, and software combinations
  - [x] Ensured data includes realistic values for all mapped fields (GC, N50, contigs, completeness, contamination, etc.)
  - [x] Validated that test data triggers expected outcomes across QC tests
  - [x] Test data successfully demonstrates rule filtering logic and QC outcome determination
- [ ] Implement `app.py` Streamlit web application
- [ ] Implement `plot.py` plotting module
- [ ] Create sample selection and filtering functionality
- [ ] Implement QC rule processing engine
- [ ] Add data visualization components
- [ ] Implement API integration for sample handling
- [ ] Add comprehensive error handling and validation
- [ ] Create unit tests for all components
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
├── uQCme.py                 # CLI QC processor (planned)
├── app.py                   # Streamlit web app (skeleton)
├── plot.py                  # Plotting utilities (planned)
├── input/example/           # Sample data files
│   ├── run_data.tsv        # Sequencing metrics (cleaned)
│   ├── mapping.yaml        # Column mappings
│   ├── QC_rules.tsv       # Quality control rules
│   └── QC_tests.tsv       # QC outcome definitions
├── output/                 # Generated results
├── log/                   # Application logs
└── tests/                 # Test suite (planned)
```

---

*This changelog tracks both completed work and planned development for the uQCme project.*
