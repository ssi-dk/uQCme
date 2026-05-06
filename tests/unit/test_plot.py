"""Tests for dashboard plotting metric selection."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.app.plot import get_available_metrics, validate_metric_for_plotting


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

    assert get_available_metrics(data) == [
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

    assert validate_metric_for_plotting(data, "Average_Coverage") is True
    assert validate_metric_for_plotting(data, "RunID") is False
    assert validate_metric_for_plotting(data, "notes") is False
