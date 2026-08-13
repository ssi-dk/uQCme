"""Tests for resolving and applying FilteringSection presets."""

import sys
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

# Add src to path for the repository's source-layout test convention.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.core.filtering import (
    apply_filtering_section,
    resolve_filtering_sections,
)
from uQCme.core.mapping import parse_filtering_sections


def _resolved_section(columns, filters, data):
    """Parse and resolve one synthetic FilteringSection."""
    config = parse_filtering_sections(
        {"FilteringSections": {"Test view": {"columns": columns, "filters": filters}}}
    )
    return resolve_filtering_sections(config, data)["Test view"]


def _column(mapping):
    """Build a mapping-style display column."""
    return {"data": {"mapping": mapping}}


def _equals(mapping, value):
    """Build an equals condition."""
    return {
        "data": {"mapping": mapping},
        "operator": "equals",
        "value": value,
    }


def test_data_mapping_wins_when_both_sources_are_available():
    """The data mapping has precedence over QC mapping."""
    data = pd.DataFrame({"data_column": [1], "qc_column": [2]})
    section = _resolved_section(
        {
            "Metric": {
                "data": {"mapping": "data_column"},
                "QC": {"mapping": "qc_column"},
            }
        },
        {},
        data,
    )

    assert section.available is True
    assert section.columns[0].column == "data_column"


def test_qc_string_mapping_is_used_when_data_mapping_is_missing():
    """A QC mapping string is the second resolution choice."""
    data = pd.DataFrame({"qc_column": [2]})
    section = _resolved_section(
        {"Metric": {"data": {"mapping": "missing"}, "QC": {"mapping": "qc_column"}}},
        {},
        data,
    )

    assert section.columns[0].column == "qc_column"


def test_first_available_qc_mapping_list_entry_is_selected():
    """An ordered QC mapping list resolves to its first available column."""
    data = pd.DataFrame({"second": [2], "third": [3]})
    section = _resolved_section(
        {"Metric": {"QC": {"mapping": ["missing", "second", "third"]}}},
        {},
        data,
    )

    assert section.columns[0].column == "second"


def test_resolution_preserves_available_display_column_order_and_warns():
    """Missing display columns are omitted without reordering available ones."""
    data = pd.DataFrame({"first": [1], "third": [3]})
    section = _resolved_section(
        {
            "First": _column("first"),
            "Missing": _column("missing"),
            "Third": _column("third"),
        },
        {},
        data,
    )

    assert section.available is True
    assert [column.column for column in section.columns] == ["first", "third"]
    assert "display column 'Missing'" in section.warnings[0]


def test_missing_filter_column_disables_preset_fail_closed():
    """A missing filter must not produce a broader, partially filtered view."""
    data = pd.DataFrame({"sample": ["S1", "S2"]})
    section = _resolved_section(
        {"Sample": _column("sample")},
        {"Group": _equals("missing_group", "local")},
        data,
    )

    assert section.available is False
    assert "filter 'Group'" in section.warnings[0]
    assert apply_filtering_section(data, section) is None


def test_all_missing_display_columns_disable_preset():
    """A preset without any resolved display columns is unavailable."""
    data = pd.DataFrame({"sample": ["S1"]})
    section = _resolved_section(
        {"Missing": _column("missing")},
        {},
        data,
    )

    assert section.available is False
    assert any(
        "no available display columns" in warning for warning in section.warnings
    )


@pytest.mark.parametrize(
    ("operator", "condition", "expected_samples"),
    [
        (
            "equals",
            _equals("status", "PASS"),
            ["S1"],
        ),
        (
            "in",
            {
                "data": {"mapping": "group"},
                "operator": "in",
                "values": ["local", "regional"],
            },
            ["S1", "S2"],
        ),
        (
            "contains",
            {
                "data": {"mapping": "species"},
                "operator": "contains",
                "value": "COLI",
            },
            ["S1", "S2"],
        ),
        (
            "range",
            {
                "data": {"mapping": "coverage"},
                "operator": "range",
                "min": 10,
                "max": 20,
            },
            ["S1", "S2"],
        ),
    ],
)
def test_supported_operators_exclude_missing_values(
    operator, condition, expected_samples
):
    """Each preset operator applies the expected missing-safe row mask."""
    del operator
    data = pd.DataFrame(
        {
            "sample": ["S1", "S2", "S3", "S4"],
            "status": ["PASS", "FAIL", None, "OTHER"],
            "group": ["local", "regional", None, "other"],
            "species": ["Escherichia coli", "E. COLI", None, "Listeria"],
            "coverage": ["10", 20, "not numeric", None],
        }
    )
    section = _resolved_section(
        {"Sample": _column("sample")},
        {"Condition": condition},
        data,
    )

    result = apply_filtering_section(data, section)

    assert result is not None
    assert result["sample"].tolist() == expected_samples


@pytest.mark.parametrize(
    ("bounds", "expected_samples"),
    [
        ({"min": 15}, ["S2", "S3"]),
        ({"max": 15}, ["S1", "S2"]),
        ({"min": 10, "max": 20}, ["S1", "S2", "S3"]),
    ],
)
def test_range_supports_lower_upper_and_inclusive_two_sided_bounds(
    bounds, expected_samples
):
    """Ranges accept one or both inclusive numeric bounds."""
    data = pd.DataFrame(
        {"sample": ["S1", "S2", "S3", "S4"], "coverage": [10, 15, 20, None]}
    )
    condition = {"data": {"mapping": "coverage"}, "operator": "range", **bounds}
    section = _resolved_section(
        {"Sample": _column("sample")},
        {"Coverage": condition},
        data,
    )

    result = apply_filtering_section(data, section)

    assert result is not None
    assert result["sample"].tolist() == expected_samples


def test_multiple_conditions_use_and_logic_and_allow_empty_results():
    """Every configured condition must match for a row to remain."""
    data = pd.DataFrame(
        {
            "sample": ["S1", "S2", "S3"],
            "status": ["PASS", "PASS", "FAIL"],
            "coverage": [10, 20, 10],
        }
    )
    section = _resolved_section(
        {"Sample": _column("sample")},
        {
            "Status": _equals("status", "PASS"),
            "Coverage": {
                "data": {"mapping": "coverage"},
                "operator": "range",
                "min": 30,
            },
        },
        data,
    )

    result = apply_filtering_section(data, section)

    assert result is not None
    assert result.empty
    assert list(result.columns) == list(data.columns)


def test_apply_returns_copy_and_does_not_mutate_input_dataframe():
    """Preset filtering must leave the complete baseline dataframe unchanged."""
    data = pd.DataFrame({"sample": ["S1", "S2"], "status": ["PASS", "FAIL"]})
    original = data.copy(deep=True)
    section = _resolved_section(
        {"Sample": _column("sample")},
        {"Status": _equals("status", "PASS")},
        data,
    )

    result = apply_filtering_section(data, section)

    assert result is not None
    assert result is not data
    assert_frame_equal(data, original)


def test_resolve_filtering_sections_preserves_preset_order():
    """Resolved presets retain the YAML declaration order for downstream UI."""
    data = pd.DataFrame({"first": [1], "second": [2]})
    config = parse_filtering_sections(
        {
            "FilteringSections": {
                "First": {"columns": {"A": _column("first")}, "filters": {}},
                "Second": {"columns": {"B": _column("second")}, "filters": {}},
            }
        }
    )

    resolved = resolve_filtering_sections(config, data)

    assert list(resolved) == ["First", "Second"]
