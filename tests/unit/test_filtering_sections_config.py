"""Tests for the FilteringSections mapping boundary contract."""

import sys
from pathlib import Path

import pytest

# Add src to path for the repository's source-layout test convention.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.core.exceptions import ConfigError
from uQCme.core.mapping import parse_filtering_sections


def _valid_mapping():
    """Return a valid mapping with two ordered FilteringSections."""
    return {
        "FilteringSections": {
            "Local group": {
                "columns": {
                    "Sample": {"data": {"mapping": "sample_name"}},
                    "QC outcome": {"data": {"mapping": "qc_outcome"}},
                },
                "filters": {
                    "Group": {
                        "data": {"mapping": "group_name"},
                        "operator": "equals",
                        "value": "local",
                    }
                },
            },
            "Regional group": {
                "columns": {
                    "Sample": {"data": {"mapping": "sample_name"}},
                },
                "filters": {
                    "Group": {
                        "data": {"mapping": "group_name"},
                        "operator": "in",
                        "values": ["regional", "shared"],
                    }
                },
            },
        }
    }


def test_valid_filtering_sections_preserve_declaration_order():
    """Preset, column, and filter order should survive boundary parsing."""
    parsed = parse_filtering_sections(_valid_mapping())

    assert list(parsed.sections) == ["Local group", "Regional group"]
    assert list(parsed.sections["Local group"].columns) == [
        "Sample",
        "QC outcome",
    ]
    assert list(parsed.sections["Local group"].filters) == ["Group"]


def test_filtering_sections_accept_all_supported_condition_shapes():
    """All first-version operators should parse as typed conditions."""
    mapping = {
        "FilteringSections": {
            "All operators": {
                "columns": {
                    "Sample": {"data": {"mapping": "sample_name"}},
                },
                "filters": {
                    "Equals": {
                        "data": {"mapping": "status"},
                        "operator": "equals",
                        "value": "PASS",
                    },
                    "Membership": {
                        "data": {"mapping": "group"},
                        "operator": "in",
                        "values": ["local", "regional"],
                    },
                    "Contains": {
                        "data": {"mapping": "species"},
                        "operator": "contains",
                        "value": "coli",
                    },
                    "Range": {
                        "data": {"mapping": "coverage"},
                        "operator": "range",
                        "min": 10,
                        "max": 100,
                    },
                },
            }
        }
    }

    parsed = parse_filtering_sections(mapping)
    operators = [
        condition.operator
        for condition in parsed.sections["All operators"].filters.values()
    ]

    assert operators == ["equals", "in", "contains", "range"]


def test_qc_mapping_string_and_ordered_list_are_kept():
    """Mapping references retain the string/list shape needed for later fallback."""
    mapping = {
        "FilteringSections": {
            "QC fallback": {
                "columns": {
                    "Metric": {"QC": {"mapping": ["first_metric", "second_metric"]}},
                },
                "filters": {
                    "Status": {
                        "QC": {"mapping": "status"},
                        "operator": "equals",
                        "value": "PASS",
                    }
                },
            }
        }
    }

    parsed = parse_filtering_sections(mapping)
    column_reference = parsed.sections["QC fallback"].columns["Metric"]
    filter_reference = parsed.sections["QC fallback"].filters["Status"]

    assert column_reference.QC.mapping == ["first_metric", "second_metric"]
    assert filter_reference.QC.mapping == "status"


def test_absent_filtering_sections_returns_empty_collection():
    """Legacy mappings without the new top-level key remain valid."""
    parsed = parse_filtering_sections({"Sections": {"Basic": {}}})

    assert parsed.sections == {}


def test_mapping_source_allows_existing_metadata():
    """Mapping references may carry metadata used by other mapping features."""
    mapping = _valid_mapping()
    mapping["FilteringSections"]["Local group"]["columns"]["Sample"]["data"][
        "unique"
    ] = True

    parsed = parse_filtering_sections(mapping)

    assert parsed.sections["Local group"].columns["Sample"].data.mapping == (
        "sample_name"
    )


def test_non_mapping_yaml_root_is_rejected():
    """A malformed YAML root should not be treated as a legacy mapping."""
    with pytest.raises(ConfigError, match="mapping at its root"):
        parse_filtering_sections(["not", "a", "mapping"])


@pytest.mark.parametrize(
    "condition",
    [
        {
            "data": {"mapping": "status"},
            "operator": "unsupported",
            "value": "PASS",
        },
        {
            "data": {"mapping": "group"},
            "operator": "in",
            "values": [],
        },
        {
            "data": {"mapping": "group"},
            "operator": "in",
        },
        {
            "data": {"mapping": "status"},
            "operator": "equals",
        },
        {
            "data": {"mapping": "species"},
            "operator": "contains",
        },
        {
            "data": {"mapping": "coverage"},
            "operator": "range",
        },
        {
            "data": {"mapping": "coverage"},
            "operator": "range",
            "min": "not numeric",
        },
    ],
)
def test_malformed_operator_value_combinations_are_rejected(condition):
    """Malformed conditions should fail before dashboard rendering."""
    mapping = {
        "FilteringSections": {
            "Malformed": {
                "columns": {
                    "Sample": {"data": {"mapping": "sample_name"}},
                },
                "filters": {"Bad condition": condition},
            }
        }
    }

    with pytest.raises(ConfigError):
        parse_filtering_sections(mapping)


@pytest.mark.parametrize("missing_key", ["columns", "filters"])
def test_filtering_section_requires_columns_and_filters(missing_key):
    """Each configured preset must declare both mapping collections."""
    section = {
        "columns": {"Sample": {"data": {"mapping": "sample_name"}}},
        "filters": {
            "Status": {
                "data": {"mapping": "status"},
                "operator": "equals",
                "value": "PASS",
            }
        },
    }
    del section[missing_key]

    with pytest.raises(ConfigError):
        parse_filtering_sections({"FilteringSections": {"Incomplete": section}})


def test_invalid_mapping_reports_filtering_section_context():
    """Boundary errors should identify the new mapping area and preset."""
    mapping = _valid_mapping()
    mapping["FilteringSections"]["Local group"]["filters"]["Group"].pop("value")

    with pytest.raises(ConfigError) as error:
        parse_filtering_sections(mapping)

    message = str(error.value)
    assert "FilteringSections" in message
    assert "Local group" in message
