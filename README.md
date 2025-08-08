# uQCme - Microbial Quality Control Tool

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A comprehensive quality control (QC) tool for microbial sequencing data that provides both command-line processing and interactive web-based visualization capabilities.

## Overview

uQCme consists of two main components:

1. **CLI Tool** (`uQCme.py`): Processes microbial sequencing QC data against configurable quality control rules
2. **Web Dashboard** (`app.py`): Interactive Streamlit application for visualizing and exploring QC results

## Features

### Core Functionality
- **Species-specific QC rules**: Support for 17+ microbial species with tailored quality control criteria
- **Configurable QC tests**: Define custom QC outcomes with priority-based rule conditions
- **Flexible rule engine**: Regex-based validation with threshold checks for various QC metrics
- **Interactive dashboard**: Web-based visualization with filtering, sorting, and detailed sample exploration
- **Comprehensive logging**: Detailed logging system with both file and console output

### Supported Species
- Acinetobacter baumannii
- Campylobacter coli & jejuni
- Escherichia coli
- Enterococcus faecium
- Enterobacter spp.
- Haemophilus influenzae
- Helicobacter pylori
- Klebsiella pneumoniae
- Mycoplasma genitalium
- Neisseria gonorrhoeae
- Pseudomonas aeruginosa
- Staphylococcus aureus
- Salmonella enterica
- Shigella flexneri & sonnei
- Streptococcus pneumoniae

### QC Metrics
- Assembly statistics (N50, contigs, genome size)
- CheckM completeness and contamination
- Species identification validation
- Coverage depth analysis
- Quality score assessments

## Installation

### Using Pixi (Recommended)

```bash
git clone https://github.com/ssi-dk/uQCme.git
cd uQCme
pixi install
```

### Using pip

```bash
git clone https://github.com/ssi-dk/uQCme.git
cd uQCme
pip install -r requirements.txt
```

### Dependencies

- Python 3.8+
- streamlit >=1.47.1
- pandas >=2.3.1
- plotly >=6.2.0
- pyyaml >=6.0.2
- openpyxl >=3.1.5

## Quick Start

### 1. Command Line Processing

Process your QC data using the CLI tool:

```bash
python uQCme.py --config config.yaml
```

### 2. Launch Web Dashboard

Start the interactive dashboard:

```bash
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`

## Configuration

uQCme uses a YAML configuration file (`config.yaml`) to specify input/output paths and application settings:

```yaml
title: "uQCme - Microbial QC Reporter"
version: "0.1.0"

qc:
  input:
    data: "./input/example/run_data.tsv"
    mapping: "./input/example/mapping.yaml"
    qc_rules: "./input/example/QC_rules.tsv"
    qc_tests: "./input/example/QC_tests.tsv"
  output:
    results: "./output/example/uQCme_run_data.tsv"
    warnings: "./output/example/uQCme_rule_warnings.tsv"

app:
  server:
    host: "127.0.0.1"
    port: 3838
  dashboard:
    categorical_filter_threshold: 20
    section_toggle_columns: 3
    max_displayed_rules: 10
  priority_colors:
    1: "#90EE90"  # Pass - Light Green
    2: "#FFFFE0"  # Warning - Light Yellow
    3: "#F08080"  # Fail - Light Coral
    4: "#FFB6C1"  # Critical - Light Pink
```

## Input Files

### 1. Run Data (`run_data.tsv`)
Tab-separated file containing QC metrics for each sample:
- Sample identifiers
- Assembly statistics (contigs, N50, genome size)
- CheckM results (completeness, contamination, marker lineage)
- Coverage and quality metrics

### 2. QC Rules (`QC_rules.tsv`)
Defines validation rules for each QC metric:
- Rule ID and species association
- QC tool and metric specifications
- Validation type (threshold, regex, etc.)
- Threshold values and conditions

### 3. QC Tests (`QC_tests.tsv`)
Defines QC outcomes and their conditions:
- Outcome ID and descriptive name
- Priority level (1=Pass, 2=Warning, 3=Fail, 4=Critical)
- Rule conditions for outcome assignment
- Required actions

### 4. Mapping Configuration (`mapping.yaml`)
Maps QC tools to their respective data columns and display settings.

## Output Files

### 1. QC Results (`uQCme_run_data.tsv`)
Enhanced run data with QC outcomes:
- Original sample data
- Failed rules per sample
- Assigned QC outcome with priority
- Color coding for visualization

### 2. Rule Warnings (`uQCme_rule_warnings.tsv`)
Detailed log of rule evaluation issues:
- Skipped rules and reasons
- Data validation warnings
- Processing statistics

## Dashboard Features

### Data Overview
- Interactive data table with filtering and sorting
- Priority-based color coding of QC outcomes
- Summary statistics and sample counts

### Sample Details
- Detailed view of individual sample QC results
- Failed rules and thresholds
- Interactive metric exploration

### Visualization
- Plotly-based interactive charts
- Customizable metric comparisons
- Species-specific analysis views

### Filtering and Search
- Dynamic filtering by QC outcome, species, and metrics
- Search functionality across all data columns
- Export capabilities for filtered datasets

## Advanced Usage

### Custom QC Rules

Create custom QC rules by editing `QC_rules.tsv`:

```tsv
rule_id	species	qc_tool	qc_metric	validation_type	threshold	column_name
CUSTOM1	Escherichia coli	Assembly	N50	threshold	>=50000	n50
CUSTOM2	all	CheckM	Completeness	threshold	>=90	completeness
```

### Species-Specific Tests

Define new QC tests in `QC_tests.tsv`:

```tsv
outcome_id	outcome_name	description	priority	rule_conditions	action_required
FAIL_CUSTOM	Fail - Custom QC	Custom quality control failed	3	failed_rules_contain:CUSTOM1,CUSTOM2	reject
```

## Development

### Project Structure

```
uQCme/
├── app.py              # Streamlit web dashboard
├── uQCme.py           # CLI processing tool
├── plot.py            # Plotting utilities
├── config.yaml        # Configuration file
├── input/
│   └── example/       # Example input files
├── output/            # Generated results
├── log/               # Application logs
└── tests/             # Unit tests
```

### Running Tests

```bash
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Missing input files**: Ensure all required input files exist and paths in `config.yaml` are correct
2. **Rule validation errors**: Check that QC rules reference valid column names in your data
3. **Dashboard not loading**: Verify Streamlit installation and port availability

### Logging

Check the log file (`./log/log.tsv`) for detailed processing information:

```bash
tail -f ./log/log.tsv
```

## Citation

If you use uQCme in your research, please cite:

```
uQCme: A Comprehensive Quality Control Tool for Microbial Sequencing Data
SSI-DK, 2025
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or feature requests:

- Create an issue on GitHub
- Contact: Kim Ng (kimleeng@gmail.com)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
