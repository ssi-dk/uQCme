"""Tests for dashboard plotting metric selection."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.app.plot import (
    build_quality_metric_catalog,
    get_available_metrics,
    get_plottable_quality_metric_columns,
    validate_metric_for_plotting,
)


def test_get_available_metrics_accepts_numeric_strings_and_excludes_ids():
    """API payloads may encode metric values as strings."""
    data = pd.DataFrame(
        {
            "Runid": ["1001", "1002"],
            "RunID": [1001, 1002],
            "SeqSampleID": ["501", "502"],
            "sample_name": ["S1", "S2"],
            "species": ["Escherichia coli", "Listeria monocytogenes"],
            "qc_outcome": ["PASS", "FAIL"],
            "Average_Coverage": ["42.5", "87.1"],
            "fastp_Before_Filtering_Total_Reads": ["1000", "2500"],
            "notes": ["not numeric", "still not numeric"],
            "empty_metric": ["", None],
            "nested_payload": [{"value": 1}, {"value": 2}],
        }
    )
    mapping = {
        "Sections": {
            "Basic": {
                "Run ID": {
                    "data": {"mapping": "Runid"},
                    "report": {"id": True},
                },
                "Run ID Canonical": {
                    "data": {"mapping": "RunID"},
                    "report": {"id": True},
                },
                "SeqSample ID": {
                    "data": {"mapping": "SeqSampleID"},
                    "report": {"id": True},
                },
            }
        }
    }

    assert get_available_metrics(data, mapping) == [
        "Average_Coverage",
        "fastp_Before_Filtering_Total_Reads",
    ]


def test_validate_metric_for_plotting_requires_numeric_values():
    data = pd.DataFrame(
        {
            "RunID": ["1001"],
            "Average_Coverage": ["42.5"],
            "notes": ["not numeric"],
        }
    )

    mapping = {
        "Sections": {
            "Basic": {
                "Run ID": {
                    "data": {"mapping": "RunID"},
                    "report": {"id": True},
                },
            }
        }
    }

    assert validate_metric_for_plotting(data, "Average_Coverage") is True
    assert validate_metric_for_plotting(data, "RunID", mapping) is False
    assert validate_metric_for_plotting(data, "notes") is False


def test_quality_metric_catalog_uses_qc_mapping_without_section_names():
    data = pd.DataFrame(
        {
            "coverage_x": ["45.5", "30"],
            "species": ["A", "B"],
        }
    )
    mapping = {
        "Sections": {
            "Measurements": {
                "Coverage": {
                    "data": {"mapping": "coverage_x"},
                    "QC": {"mapping": ["Coverage", "coverage_x"]},
                }
            }
        }
    }
    qc_rules = pd.DataFrame([
        {"field": "Coverage"},
        {"field": "coverage_x"},
    ])

    catalog = build_quality_metric_catalog(data, mapping, qc_rules)

    assert len(catalog) == 1
    assert catalog[0].label == "Coverage"
    assert catalog[0].data_column == "coverage_x"
    assert catalog[0].rule_fields == ("Coverage", "coverage_x")
    assert catalog[0].section == "Measurements"
    assert catalog[0].plottable is True
    assert get_plottable_quality_metric_columns(catalog) == ["coverage_x"]


def test_quality_metric_catalog_honors_explicit_include_and_exclude():
    data = pd.DataFrame(
        {
            "explicit_metric": ["A", "B"],
            "excluded_metric": ["1", "2"],
        }
    )
    mapping = {
        "Sections": {
            "Basic": {
                "Explicit Metric": {
                    "data": {"mapping": "explicit_metric"},
                    "report": {"quality_metric": True},
                },
            },
            "Read_QC": {
                "Excluded Metric": {
                    "data": {"mapping": "excluded_metric"},
                    "QC": {"mapping": "ExcludedField"},
                    "report": {"quality_metric": False},
                },
            },
        }
    }
    qc_rules = pd.DataFrame([
        {"field": "ExcludedField"},
    ])

    catalog = build_quality_metric_catalog(data, mapping, qc_rules)

    assert [entry.label for entry in catalog] == ["Explicit Metric"]
    assert catalog[0].plottable is False
    assert catalog[0].non_plottable_reason == "non-numeric/categorical"


def test_quality_metric_catalog_reports_missing_and_empty_reasons():
    data = pd.DataFrame({
        "empty_metric": [None, ""],
    })
    mapping = {
        "Sections": {
            "Read_QC": {
                "Missing Metric": {
                    "data": {"mapping": "missing_metric"},
                    "QC": {"mapping": "MissingField"},
                },
                "Empty Metric": {
                    "data": {"mapping": "empty_metric"},
                    "QC": {"mapping": "EmptyField"},
                },
            }
        }
    }
    qc_rules = pd.DataFrame([
        {"field": "MissingField"},
        {"field": "EmptyField"},
    ])

    catalog = build_quality_metric_catalog(data, mapping, qc_rules)
    reasons = {
        entry.label: entry.non_plottable_reason
        for entry in catalog
    }

    assert reasons == {
        "Missing Metric": "missing column",
        "Empty Metric": "all values empty",
    }
